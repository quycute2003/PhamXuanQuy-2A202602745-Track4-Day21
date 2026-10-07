"""Topic A: calibration yaw sweep with a fixed object-point denominator.

Source: CP3 codelab supplied with this assignment (points_in_box and sweep idea).
Extensions: fixed denominator, equal object weighting, per-object/class/range
results, explicit empty-box counts, and visible-only reference metric.
Run from the repository root: python -m src.exp_yaw_sweep --help
No random sampling is used.
"""
from __future__ import annotations

import argparse
import csv
from pathlib import Path

import numpy as np

from starter.datasets import load_frame
from starter.projection import perturb_extrinsic, project_velo_to_image, velo_to_cam

CLASSES = ("Car", "Pedestrian")
FRAMES = ("000019", "000011", "000004", "000049")
YAW_LEVELS = (0.0, 0.5, 1.0, 2.0, 3.0)


def points_in_box(points_cam, obj):
    """KITTI box: bottom center, dimensions (h,w,l), rotation about camera y."""
    h, w, length = obj.dimensions
    c, s = np.cos(obj.rotation_y), np.sin(obj.rotation_y)
    rotation = np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])
    finite = np.isfinite(points_cam).all(axis=1)
    local = np.full(points_cam.shape, np.nan, dtype=float)
    local[finite] = (points_cam[finite] - obj.location) @ rotation
    return (finite & (np.abs(local[:, 0]) <= length / 2)
            & (local[:, 1] <= 0) & (local[:, 1] >= -h)
            & (np.abs(local[:, 2]) <= w / 2))


def score_object(selection, uv_all, bbox):
    """Out-of-image points have NaN pixels: count them as misses, not exclusions."""
    pixels = uv_all[selection]
    x1, y1, x2, y2 = bbox
    visible = np.isfinite(pixels).all(axis=1)
    hits = int((visible & (pixels[:, 0] >= x1) & (pixels[:, 0] <= x2)
                & (pixels[:, 1] >= y1) & (pixels[:, 1] <= y2)).sum())
    count = int(selection.sum())
    return {"object_points": count, "visible_object_points": int(visible.sum()),
            "hit_points": hits, "hit_ratio": hits / count if count else float("nan")}


def prepare_frame(fr, classes=CLASSES):
    points = fr["points"][np.isfinite(fr["points"][:, :3]).all(axis=1)]
    cam_true = velo_to_cam(points[:, :3], fr["calib"])
    objects = [(i, obj, points_in_box(cam_true, obj))
               for i, obj in enumerate(fr["labels"]) if obj.type in classes]
    return {"frame": fr, "points": points, "objects": objects}


def summarize(rows):
    nonempty = [r for r in rows if r["object_points"] > 0]
    total = sum(r["object_points"] for r in rows)
    visible = sum(r["visible_object_points"] for r in rows)
    hits = sum(r["hit_points"] for r in rows)
    return {"object_count": len(nonempty), "empty_object_count": len(rows) - len(nonempty),
            "object_points": total, "visible_object_points": visible, "hit_points": hits,
            "mean_hit_ratio": float(np.mean([r["hit_ratio"] for r in nonempty])) if nonempty else float("nan"),
            "pooled_hit_ratio": hits / total if total else float("nan"),
            "visible_hit_ratio": hits / visible if visible else float("nan")}


def run_one(prepared, yaw_deg):
    fr, points = prepared["frame"], prepared["points"]
    calib = perturb_extrinsic(fr["calib"], yaw_deg=yaw_deg)
    uv, _, mask = project_velo_to_image(points, calib, fr["image"].shape)
    uv_all = np.full((len(points), 2), np.nan)
    uv_all[mask] = uv
    objects = []
    for object_id, obj, selection in prepared["objects"]:
        distance = float(np.hypot(obj.location[0], obj.location[2]))
        objects.append({"object_id": object_id, "type": obj.type,
                        "distance_m": distance,
                        "range_bin": "0-15m" if distance < 15 else "15-30m" if distance < 30 else "30m+",
                        "occluded": obj.occluded, "truncated": obj.truncated,
                        **score_object(selection, uv_all, obj.bbox)})
    row = {"n_points_raw": len(fr["points"]), "n_points": len(points),
           "inside_image": int(mask.sum()), "fov_ratio": float(mask.mean()) if len(mask) else float("nan"),
           **summarize(objects)}
    return row, objects


def write_csv(path, rows, fields=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields or list(rows[0]))
        writer.writeheader()
        for row in rows:
            writer.writerow({key: format(value, ".12g") if isinstance(value, float) else value
                             for key, value in row.items()})
    print(f"-> {path} ({len(rows)} rows)")


def output_paths(out):
    return {"frames": out,
            **{kind: out.with_name(f"{out.stem}_{kind}.csv") for kind in ("objects", "groups", "summary")}}


def main():
    parser = argparse.ArgumentParser(description="Yaw sweep: fixed GT points, per-object mean, class/range splits")
    parser.add_argument("--data-root", default="data/kitti_mini")
    parser.add_argument("--frames", nargs="+", default=list(FRAMES))
    parser.add_argument("--yaw-levels", nargs="+", type=float, default=list(YAW_LEVELS))
    parser.add_argument("--classes", nargs="+", default=list(CLASSES))
    parser.add_argument("--out", type=Path, default=Path("results/yaw_perturb_sweep.csv"))
    args = parser.parse_args()
    if 0 not in args.yaw_levels or not np.isfinite(args.yaw_levels).all():
        parser.error("--yaw-levels must include baseline 0 and contain only finite values")
    if len(set(args.yaw_levels)) != len(args.yaw_levels) or len(set(args.frames)) != len(args.frames):
        parser.error("duplicate yaw levels or frames would double-count results")
    if "DontCare" in args.classes:
        parser.error("DontCare is excluded from object evaluation")

    frame_rows, object_rows = [], []
    dataset = Path(args.data_root).name
    for frame_id in args.frames:
        prepared = prepare_frame(load_frame(args.data_root, frame_id), args.classes)
        for yaw in sorted(args.yaw_levels):
            prefix = {"dataset": dataset, "frame": frame_id, "classes": "|".join(args.classes), "yaw_deg": yaw}
            row, objects = run_one(prepared, yaw)
            frame_rows.append({**prefix, **row})
            object_rows.extend({**prefix, **obj} for obj in objects)
            print(f"{frame_id} yaw={yaw:g}: objects={row['object_count']} "
                  f"mean_hit={100 * row['mean_hit_ratio']:.2f}% FOV={100 * row['fov_ratio']:.2f}%")

    summaries, groups = [], []
    for yaw in sorted(args.yaw_levels):
        objects = [r for r in object_rows if r["yaw_deg"] == yaw]
        frames = [r for r in frame_rows if r["yaw_deg"] == yaw]
        count = sum(r["n_points"] for r in frames)
        inside = sum(r["inside_image"] for r in frames)
        summaries.append({"dataset": dataset, "classes": "|".join(args.classes), "yaw_deg": yaw,
                          "frame_count": len(frames), "n_points": count, "inside_image": inside,
                          "fov_ratio": inside / count if count else float("nan"), **summarize(objects)})
        for kind, field, values in (("class", "type", args.classes),
                                    ("range", "range_bin", ("0-15m", "15-30m", "30m+"))):
            for value in values:
                selected = [r for r in objects if r[field] == value]
                groups.append({"dataset": dataset, "yaw_deg": yaw, "group_kind": kind,
                               "group": value, **summarize(selected)})
    baseline = next(r["mean_hit_ratio"] for r in summaries if r["yaw_deg"] == 0)
    for row in summaries:
        row["drop_vs_baseline_pp"] = 100 * (baseline - row["mean_hit_ratio"])
    paths = output_paths(args.out)
    write_csv(paths["frames"], frame_rows)
    object_fields = ["dataset", "frame", "classes", "yaw_deg", "object_id", "type", "distance_m",
                     "range_bin", "occluded", "truncated", "object_points", "visible_object_points",
                     "hit_points", "hit_ratio"]
    write_csv(paths["objects"], object_rows, object_fields)
    write_csv(paths["groups"], groups)
    write_csv(paths["summary"], summaries)


if __name__ == "__main__":
    main()
