"""Plot CP3 results. Adapted from the plotting idea in the supplied CP3 codelab.

Extensions: four panels, fixed-denominator object means and class/range splits.
Run from the repository root: python -m src.plot_yaw_sweep --help
"""
import argparse
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from src.exp_yaw_sweep import output_paths


def main():
    parser = argparse.ArgumentParser(description="Plot frame, class, range and FOV yaw results")
    parser.add_argument("--csv", type=Path, default=Path("results/yaw_perturb_sweep.csv"), help="Frame CSV; sibling group/summary CSVs must exist")
    parser.add_argument("--out", type=Path, default=Path("results/figures/yaw_sweep.png"), help="Output PNG path")
    args = parser.parse_args()
    paths = output_paths(args.csv)
    frames = pd.read_csv(paths["frames"], dtype={"frame": str})
    groups = pd.read_csv(paths["groups"])
    summary = pd.read_csv(paths["summary"])
    fig, axes = plt.subplots(2, 2, figsize=(12, 8), layout="constrained")

    for frame, rows in frames.groupby("frame", sort=False):
        axes[0, 0].plot(rows["yaw_deg"], 100 * rows["mean_hit_ratio"], marker="o", label=frame)
    axes[0, 0].plot(summary["yaw_deg"], 100 * summary["mean_hit_ratio"],
                    color="black", linewidth=2.5, linestyle="--", marker="s", label="All objects")
    axes[0, 0].set_title("Fixed GT points: mean per object, by frame")
    for ax, kind, title in ((axes[0, 1], "class", "Mean per object, by class"),
                            (axes[1, 0], "range", "Mean per object, by ground-plane distance")):
        for label, rows in groups[groups["group_kind"] == kind].groupby("group", sort=False):
            ax.plot(rows["yaw_deg"], 100 * rows["mean_hit_ratio"], marker="o", label=label)
        ax.set_title(title)
    axes[1, 1].plot(summary["yaw_deg"], 100 * summary["mean_hit_ratio"], marker="o", label="Object hit ratio")
    axes[1, 1].plot(summary["yaw_deg"], 100 * summary["fov_ratio"], marker="s", label="All-point FOV ratio")
    axes[1, 1].set_title("Object alignment versus FOV coverage")
    for i, ax in enumerate(axes.flat):
        ax.set_xlabel("LiDAR yaw drift (degrees)")
        ax.set_ylabel("Ratio (%)" if i == 3 else "Object points inside own 2D box (%)")
        ax.set_ylim(0, 105)
        ax.grid(alpha=0.25)
        ax.legend(fontsize=8, loc="best")
    title = f"{summary.iloc[0]['dataset']} calibration sensitivity | {summary.iloc[0]['classes']} | {len(frames['frame'].unique())} frames"
    fig.suptitle(title, fontsize=14)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.out, dpi=170)
    plt.close(fig)
    print(f"-> {args.out}")


if __name__ == "__main__":
    main()
