"""CP3 checks: box geometry, denominator, and supplied reference numbers.

Reference values/classes/frames: supplied CP3 codelab, visible-only pooled metric.
Run: python -m src.test_yaw_sweep
"""
import numpy as np

from starter.datasets import load_frame
from starter.kitti_io import KittiObject
from src.exp_yaw_sweep import points_in_box, prepare_frame, run_one, score_object, summarize


def main():
    obj = KittiObject("Car", 0, 0, 0, np.array([0, 0, 10, 10]),
                      np.array([2, 2, 4]), np.array([10, 3, 20]), np.pi / 2)
    # A 90-degree box has half-width 1 in global x and half-length 2 in global z.
    points = np.array([[10, 2, 21.9], [10, 2, 22.1], [11.1, 2, 20],
                       [10, 3.1, 20], [10, 0.9, 20], [np.nan, 2, 20]])
    assert points_in_box(points, obj).tolist() == [True, False, False, False, False, False]
    pixels = np.array([[1, 1], [np.nan, np.nan], [2, 2]])
    score = score_object(np.ones(3, dtype=bool), pixels, [0, 0, 1.5, 1.5])
    assert score["object_points"] == 3 and score["visible_object_points"] == 2
    assert score["hit_points"] == 1 and score["hit_ratio"] == 1 / 3
    empty = score_object(np.zeros(3, dtype=bool), pixels, [0, 0, 1.5, 1.5])
    assert empty["object_points"] == 0 and np.isnan(empty["hit_ratio"])
    large = {"object_points": 100, "visible_object_points": 100, "hit_points": 100, "hit_ratio": 1.0}
    small = {"object_points": 1, "visible_object_points": 1, "hit_points": 0, "hit_ratio": 0.0}
    stats = summarize([large, small, empty])
    assert stats["mean_hit_ratio"] == 0.5 and stats["pooled_hit_ratio"] == 100 / 101
    assert stats["empty_object_count"] == 1 and stats["object_count"] == 2

    expected = {"000008": [0.9963, 0.9957, 0.9862, 0.9481, 0.9098],
                "000011": [0.9945, 0.9188, 0.7744, 0.4544, 0.2123],
                "000049": [0.9925, 0.9746, 0.9350, 0.8474, 0.7432]}
    for frame, ratios in expected.items():
        prepared = prepare_frame(load_frame("data/kitti_mini", frame), ("Car", "Van", "Pedestrian", "Cyclist"))
        denominators = None
        for yaw, ratio in zip([0, 0.5, 1, 2, 3], ratios):
            result, objects = run_one(prepared, yaw)
            assert round(result["visible_hit_ratio"], 4) == ratio, (frame, yaw, result, ratio)
            current = [r["object_points"] for r in objects]
            if denominators is None:
                denominators = current
            assert current == denominators, (frame, yaw)
        print(f"{frame}: all 5 visible-only reference ratios match [PASS]")
    print("CP3 metric self-test passed")


if __name__ == "__main__":
    main()
