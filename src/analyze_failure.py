"""CP4: reproduce a narrow pedestrian projection failure and an FOV false negative.

Source: failure-analysis approach from the supplied CP4 codelab.
Uses the fixed GT selection and metric from src.exp_yaw_sweep (CP3).
Images are drawn from real KITTI pixels and projected points; no synthesized data.
Run from the repository root: python -m src.analyze_failure --help
"""
from __future__ import annotations

import argparse
from pathlib import Path

import cv2
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle
import numpy as np

from src.exp_yaw_sweep import prepare_frame, score_object, write_csv
from starter.datasets import load_frame
from starter.projection import draw_box2d, overlay_points, perturb_extrinsic, project_velo_to_image


def main():
    parser = argparse.ArgumentParser(description="CP4: annotate yaw failure on KITTI 000011, pedestrian object 3")
    parser.add_argument("--out-dir", type=Path, default=Path("results/figures"))
    parser.add_argument("--csv", type=Path, default=Path("results/failure_analysis.csv"))
    args = parser.parse_args()
    fr = load_frame("data/kitti_mini", "000011")
    prepared = prepare_frame(fr)
    object_id, obj, selection = next(item for item in prepared["objects"] if item[0] == 3)
    points = prepared["points"]
    assert obj.type == "Pedestrian" and selection.sum() == 40
    width = float(obj.bbox[2] - obj.bbox[0])
    distance = float(np.hypot(obj.location[0], obj.location[2]))
    records, outputs = [], {}
    baseline_pixels = None
    baseline_fov = None
    baseline_hit = None
    for yaw in (0, 0.5, 1, 2, 3):
        uv, depth, mask = project_velo_to_image(
            points, perturb_extrinsic(fr["calib"], yaw_deg=yaw), fr["image"].shape)
        pixels = np.full((len(points), 2), np.nan)
        pixels[mask] = uv
        selected_pixels = pixels[selection]
        stats = score_object(selection, pixels, obj.bbox)
        fov_ratio = float(mask.mean())
        if yaw == 0:
            baseline_pixels = selected_pixels.copy()
            baseline_fov = fov_ratio
            baseline_hit = stats["hit_ratio"]
        common = np.isfinite(selected_pixels).all(axis=1) & np.isfinite(baseline_pixels).all(axis=1)
        du = selected_pixels[common, 0] - baseline_pixels[common, 0]
        records.append({"dataset": "kitti_mini", "frame": "000011", "object_id": object_id,
                        "type": obj.type, "distance_m": distance, "bbox_width_px": width,
                        "occluded": obj.occluded, "truncated": obj.truncated, "yaw_deg": float(yaw),
                        **stats, "n_points": len(points), "inside_image": int(mask.sum()),
                        "fov_ratio": fov_ratio, "common_visible_points": int(common.sum()),
                        "median_du_px": float(np.median(du)) if len(du) else float("nan"),
                        "median_abs_du_px": float(np.median(np.abs(du))) if len(du) else float("nan"),
                        "fov_alarm_below_90pct_baseline": fov_ratio < 0.9 * baseline_fov,
                        "object_alarm_below_80pct_baseline": stats["hit_ratio"] < 0.8 * baseline_hit})
        outputs[yaw] = (uv, depth, selected_pixels)
    write_csv(args.csv, records)
    args.out_dir.mkdir(parents=True, exist_ok=True)

    # Context image and a pixel-coordinate zoom show exactly which object fails.
    fig, axes = plt.subplots(2, 3, figsize=(14, 6.5), layout="constrained")
    x1, y1, x2, y2 = obj.bbox
    left, right = int(np.floor(x1 - 45)), int(np.ceil(x2 + 35))
    top, bottom = int(np.floor(y1 - 25)), int(np.ceil(y2 + 25))
    crop = cv2.cvtColor(fr["image"][top:bottom, left:right], cv2.COLOR_BGR2RGB)
    for col, yaw in enumerate((0, 1, 2)):
        uv, depth, object_pixels = outputs[yaw]
        row = next(r for r in records if r["yaw_deg"] == yaw)
        image = overlay_points(fr["image"], uv, depth, radius=1)
        image = draw_box2d(image, obj.bbox, color=(0, 255, 0), label="Target ID 3")
        axes[0, col].imshow(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
        axes[0, col].add_patch(Rectangle((left, top), right-left, bottom-top,
                                       fill=False, edgecolor="yellow", linewidth=1.5))
        axes[0, col].set_title(f"Yaw +{yaw} deg | hit {row['hit_points']}/40 ({100*row['hit_ratio']:.1f}%)")
        axes[0, col].axis("off")
        ax = axes[1, col]
        ax.imshow(crop, extent=(left - 0.5, right - 0.5, bottom - 0.5, top - 0.5))
        ax.add_patch(Rectangle((x1, y1), x2-x1, y2-y1, fill=False, edgecolor="lime", linewidth=2))
        visible = np.isfinite(object_pixels).all(axis=1)
        hit = (visible & (object_pixels[:, 0] >= x1) & (object_pixels[:, 0] <= x2)
               & (object_pixels[:, 1] >= y1) & (object_pixels[:, 1] <= y2))
        for sel, color in ((hit, "cyan"), (visible & ~hit, "red")):
            ax.scatter(object_pixels[sel, 0], object_pixels[sel, 1], s=18, color=color,
                       edgecolors="black", linewidths=0.3, zorder=3)
        ax.set_xlim(left, right)
        ax.set_ylim(bottom, top)
        ax.set_xlabel("u (image pixel)")
        ax.set_ylabel("v (image pixel)")
        ax.set_title(f"Median horizontal shift: {row['median_du_px']:.2f} px")
    fig.legend(handles=[Line2D([], [], color="lime", label="Original 2D label"),
                        Line2D([], [], marker="o", linestyle="", color="cyan", label="GT object point: hit"),
                        Line2D([], [], marker="o", linestyle="", color="red", label="GT object point: miss")],
               loc="outside lower center", ncol=3)
    fig.suptitle(f"Geometry failure | KITTI 000011, pedestrian ID 3 | {distance:.2f} m | box width {width:.2f} px")
    geometry_path = args.out_dir / "fail_01_yaw_narrow_pedestrian.png"
    fig.savefig(geometry_path, dpi=170)
    plt.close(fig)

    fig, axes = plt.subplots(1, 2, figsize=(12, 4.6), layout="constrained", gridspec_kw={"width_ratios": [1.2, 1]})
    yaws = [r["yaw_deg"] for r in records]
    axes[0].plot(yaws, [100*r["hit_ratio"] for r in records], marker="o", label="Target hit ratio", color="tab:blue")
    axes[0].plot(yaws, [100*r["fov_ratio"] for r in records], marker="s", label="Whole-frame FOV ratio", color="tab:orange")
    axes[0].axhline(100*0.9*baseline_fov, color="tab:orange", linestyle="--", label="FOV alarm threshold: 90% baseline")
    axes[0].set(xlabel="LiDAR yaw drift (degrees)", ylabel="Ratio (%)", ylim=(0, 105))
    axes[0].grid(alpha=0.3)
    axes[0].legend(fontsize=8)
    axes[0].set_title("FOV-only rule misses this alignment failure")
    axes[1].axis("off")
    table = axes[1].table(cellText=[[f"{r['yaw_deg']:g}", f"{100*r['hit_ratio']:.1f}%", str(r["inside_image"]),
                                    "YES" if r["fov_alarm_below_90pct_baseline"] else "NO"] for r in records],
                          colLabels=["Yaw (deg)", "Target hit", "FOV points", "FOV alarm"],
                          loc="center", cellLoc="center")
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1, 1.8)
    for col in range(4):
        table[0, col].set_facecolor("#dce9f5")
    axes[1].set_title("40 GT points stay fixed; same frame and labels")
    fig.suptitle("Metric failure | no FOV alarm even when target hit ratio reaches 0%")
    metric_path = args.out_dir / "fail_02_fov_metric_false_negative.png"
    fig.savefig(metric_path, dpi=170)
    plt.close(fig)
    for path in (geometry_path, metric_path):
        print(f"-> {path}")
    for record in records:
        print(f"yaw={record['yaw_deg']:g} hit={record['hit_points']}/40 "
              f"median_du={record['median_du_px']:.3f}px FOV={record['inside_image']} "
              f"FOV_alarm={record['fov_alarm_below_90pct_baseline']}")


if __name__ == "__main__":
    main()
