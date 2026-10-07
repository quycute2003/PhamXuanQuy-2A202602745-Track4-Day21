"""B2/B3/B5 evidence using the same projection and GT metric as CP3.

Sources: supplied bonus codelab (stress/latency protocol), starter.perturb.
No model inference. Run from repository root: python -m src.bonus_experiments --help
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import platform
import subprocess
import time

import cv2
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src.exp_yaw_sweep import FRAMES, prepare_frame, run_one, summarize, write_csv
from starter.datasets import load_frame
from starter.perturb import gaussian_noise, random_dropout

NUSCENES_FRAMES = ("scene-0103_010", "scene-0103_020", "scene-1094_010", "scene-1094_020")


def degrade(prepared, kind, level, seed):
    original = prepared["points"]
    if kind == "dropout":
        # Carry source indices through starter's dropout so GT memberships stay fixed.
        tagged = np.column_stack([original, np.arange(len(original))])
        retained = random_dropout(tagged, keep_ratio=level, seed=seed)
        indices = retained[:, 4].astype(int)
        points = retained[:, :4].astype(original.dtype)
    else:
        points = gaussian_noise(original, sigma_xyz_m=level, seed=seed)
        indices = np.arange(len(original))
    return {"frame": prepared["frame"], "points": points,
            "objects": [(i, obj, selection[indices]) for i, obj, selection in prepared["objects"]]}


def stress(out, seeds):
    frames = [prepare_frame(load_frame("data/kitti_mini", frame)) for frame in FRAMES]
    rows, aggregated = [], []
    for kind, levels in (("dropout", (1.0, 0.7, 0.5, 0.3)), ("noise", (0.0, 0.02, 0.05, 0.1))):
        for level in levels:
            for seed in seeds:
                objects_by_yaw = {0: [], 2: []}
                fov_by_yaw = {0: [0, 0], 2: [0, 0]}
                for prepared in frames:
                    perturbed = degrade(prepared, kind, level, seed)
                    for yaw in (0, 2):
                        row, objects = run_one(perturbed, yaw)
                        prefix = {"degradation": kind, "level": level, "seed": seed,
                                  "frame": prepared["frame"]["frame_id"], "yaw_deg": float(yaw)}
                        rows.append({**prefix, **row})
                        objects_by_yaw[yaw].extend(objects)
                        fov_by_yaw[yaw][0] += row["inside_image"]
                        fov_by_yaw[yaw][1] += row["n_points"]
                for yaw, objects in objects_by_yaw.items():
                    stats = summarize(objects)
                    inside, total = fov_by_yaw[yaw]
                    aggregated.append({"degradation": kind, "level": level, "seed": seed,
                                       "yaw_deg": float(yaw), **stats,
                                       "mean_points_per_object": stats["object_points"] / stats["object_count"] if stats["object_count"] else float("nan"),
                                       "fov_ratio": inside / total if total else float("nan")})
    write_csv(out / "bonus_stress.csv", rows)
    write_csv(out / "bonus_stress_summary.csv", aggregated)
    df = pd.DataFrame(aggregated)
    across_seeds = df.groupby(["degradation", "level", "yaw_deg"], as_index=False).agg(
        seed_count=("seed", "count"), mean_hit_ratio=("mean_hit_ratio", "mean"),
        std_hit_ratio=("mean_hit_ratio", "std"), mean_points_per_object=("mean_points_per_object", "mean"),
        min_nonempty_objects=("object_count", "min"), max_empty_objects=("empty_object_count", "max"),
        mean_fov_ratio=("fov_ratio", "mean"))
    write_csv(out / "bonus_stress_aggregated.csv", across_seeds.to_dict("records"))
    fig, axes = plt.subplots(2, 2, figsize=(11, 7), layout="constrained")
    for col, kind in enumerate(("dropout", "noise")):
        subset = df[df.degradation == kind]
        for yaw, group in subset.groupby("yaw_deg"):
            grouped = group.groupby("level")
            hit = grouped.mean_hit_ratio.agg(["mean", "std"])
            axes[0, col].errorbar(hit.index, 100*hit["mean"], yerr=100*hit["std"], marker="o", capsize=3, label=f"yaw +{yaw:g} deg")
        count = subset[subset.yaw_deg == 0].groupby("level").mean_points_per_object.agg(["mean", "std"])
        axes[1, col].errorbar(count.index, count["mean"], yerr=count["std"], marker="s", capsize=3)
        axes[0, col].set(ylim=(0, 105), ylabel="Mean per-object alignment (%)", title="Random dropout" if kind == "dropout" else "Gaussian XYZ noise")
        axes[1, col].set(ylim=(0, None), ylabel="Retained GT points per nonempty object")
        for ax in axes[:, col]:
            ax.set_xlabel("Point keep ratio" if kind == "dropout" else "XYZ sigma (m)")
            ax.grid(alpha=0.25)
            if kind == "dropout":
                ax.invert_xaxis()
        axes[0, col].legend()
    fig.suptitle(f"B2 | 4 KITTI frames | {len(seeds)} fixed seeds | error bars = sample SD across seeds")
    fig.savefig(out / "figures/bonus_stress.png", dpi=160)
    plt.close(fig)


def hardware_info():
    metadata = {"platform": platform.platform(), "python": platform.python_version(),
                "numpy": np.__version__, "opencv": cv2.__version__, "pandas": pd.__version__,
                "execution": "CPU only; cached frame + GT masks; excludes I/O, GT preparation, rendering"}
    if platform.system() == "Windows":
        command = "[ordered]@{cpu=(Get-CimInstance Win32_Processor | Select-Object -ExpandProperty Name); ram_bytes=(Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory; gpu=@(Get-CimInstance Win32_VideoController | Select-Object -ExpandProperty Name)} | ConvertTo-Json -Compress"
        result = subprocess.run(["powershell", "-NoProfile", "-Command", command], capture_output=True, text=True, check=True)
        metadata.update(json.loads(result.stdout))
    else:
        metadata["cpu"] = platform.processor()
    return metadata


def latency(out, repeats):
    prepared_frames = [(frame, prepare_frame(load_frame("data/kitti_mini", frame))) for frame in FRAMES]
    metadata = hardware_info()
    metadata.update({"measured_repeats_per_frame": repeats, "warmups_per_frame": 1, "yaw_deg": 2})
    (out / "bonus_hardware.json").write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")
    rows, summaries = [], []
    for frame, prepared in prepared_frames:
        times = []
        for index in range(repeats + 1):
            start = time.perf_counter()
            run_one(prepared, 2)
            elapsed = (time.perf_counter() - start) * 1000
            rows.append({"frame": frame, "yaw_deg": 2, "run_index": index,
                         "warmup": index == 0, "elapsed_ms": elapsed})
            if index:
                times.append(elapsed)
        summaries.append({"frame": frame, "measured_runs": len(times),
                          "p50_ms": float(np.percentile(times, 50)), "p95_ms": float(np.percentile(times, 95))})
    write_csv(out / "bonus_latency.csv", rows)
    write_csv(out / "bonus_latency_summary.csv", summaries)
    print(json.dumps(metadata, ensure_ascii=False))


def compare(out):
    rows, context = [], []
    for root, frames in (("data/kitti_mini", FRAMES), ("data/nuscenes_mini_subset", NUSCENES_FRAMES)):
        dataset = Path(root).name
        for frame in frames:
            fr = load_frame(root, frame)
            fx = float(fr["calib"].P2[0, 0])
            prepared = prepare_frame(fr)
            context.append({"dataset": dataset, "frame": frame, "points": len(fr["points"]),
                            "image_width": fr["image"].shape[1], "image_height": fr["image"].shape[0],
                            "fx_px": fx, "fx_over_width": fx / fr["image"].shape[1],
                            "yaw1_shift_near_axis_px": fx*np.tan(np.deg2rad(1)),
                            "camera_minus_lidar_ms": (fr["timestamp_camera_us"]-fr["timestamp_lidar_us"])/1000 if "timestamp_camera_us" in fr else float("nan")})
        # These summaries are produced by the same CP3 script, not a second metric.
        path = out / ("yaw_perturb_sweep_summary.csv" if dataset == "kitti_mini" else "yaw_nuscenes_sweep_summary.csv")
        rows.extend(pd.read_csv(path).to_dict("records"))
    write_csv(out / "bonus_dataset_comparison.csv", rows)
    write_csv(out / "bonus_dataset_context.csv", context)
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.3), layout="constrained")
    df = pd.DataFrame(rows)
    for dataset, group in df.groupby("dataset"):
        axes[0].plot(group.yaw_deg, 100*group.mean_hit_ratio, marker="o", label=dataset)
        axes[1].plot(group.yaw_deg, group.drop_vs_baseline_pp, marker="o", label=dataset)
    axes[0].set(ylabel="Mean per-object alignment (%)", ylim=(0, 105))
    axes[1].set(ylabel="Drop from own baseline (percentage points)", ylim=(0, None))
    for ax in axes:
        ax.set_xlabel("LiDAR yaw drift (degrees)")
        ax.grid(alpha=0.25)
        ax.legend()
    fig.suptitle("B5 | Same classes, yaw levels, fixed GT denominator and object weighting")
    fig.savefig(out / "figures/bonus_dataset_comparison.png", dpi=160)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description="Bonus B2/B3/B5 evidence for projection QA")
    parser.add_argument("--mode", choices=("all", "stress", "latency", "compare"), default="all", help="Experiment to run; compare requires CP3 KITTI/nuScenes summary CSVs")
    parser.add_argument("--seeds", nargs="+", type=int, default=[0, 1, 2, 3, 4], help="Fixed random seeds for dropout and Gaussian noise")
    parser.add_argument("--repeats", type=int, default=20, help="Measured latency repetitions per frame, after one excluded warmup; minimum 20")
    parser.add_argument("--out-dir", type=Path, default=Path("results"), help="Directory for evidence CSV/JSON files and figures subdirectory")
    args = parser.parse_args()
    if args.repeats < 20 or len(set(args.seeds)) != len(args.seeds):
        parser.error("need >=20 measured repeats and unique seeds")
    (args.out_dir / "figures").mkdir(parents=True, exist_ok=True)
    # Latency runs without concurrent experiments in this process.
    if args.mode in ("all", "latency"):
        latency(args.out_dir, args.repeats)
    if args.mode in ("all", "stress"):
        stress(args.out_dir, args.seeds)
    if args.mode in ("all", "compare"):
        compare(args.out_dir)


if __name__ == "__main__":
    main()
