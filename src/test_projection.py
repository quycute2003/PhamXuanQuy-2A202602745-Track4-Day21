"""Tự kiểm tra CP2: python -m src.test_projection từ gốc repo.

Nguồn ca kiểm tra synthetic và số kỳ vọng: hướng dẫn CP2 của bài lab.
Các ca biên pinhole dùng ma trận đơn giản có thể tính tay.
"""
import numpy as np

from starter.datasets import load_frame
from starter.projection import cam_to_image, velo_to_cam


def main():
    np.set_printoptions(suppress=True, precision=2)
    fr = load_frame("data/synthetic", "000000")
    pts = np.array([
        [10.0, 0.0, 0.0],
        [np.nan, 0.0, 0.0],
        [-10.0, 0.0, 0.0],
        [10.0, 50.0, 0.0],
    ])
    cam = velo_to_cam(pts, fr["calib"])
    uv, depth, mask = cam_to_image(cam, fr["calib"].P2, fr["image"].shape)
    print("camera frame:\n", np.round(cam, 2))
    print("uv:", np.round(uv, 1), "depth:", np.round(depth, 2), "mask:", mask)
    assert cam.shape == (4, 3)
    assert abs(cam[0, 2] - 9.73) < 0.01, cam[0, 2]
    assert mask.tolist() == [True, False, False, False], mask
    assert uv.shape == (1, 2) and depth.shape == (1,)
    assert np.allclose(uv[0], [614, 175], atol=1), uv

    # u=x/z, v=y/z: ảnh chữ nhật giúp bắt lỗi nhầm H/W.
    p2 = np.eye(3, 4)
    points = np.array([
        [0, 0, 1], [7, 2, 1], [8, 2, 1], [2, 4, 1],
        [-1, 0, 1], [0, -1, 1], [0, 0, 0.1], [0, 0, -1],
        [np.nan, 0, 1], [0, np.inf, 1], [0, 0, 0],
    ], dtype=float)
    with np.errstate(all="raise"):
        uv, depth, mask = cam_to_image(points, p2, (4, 8, 3))
        assert mask.tolist() == [True, True] + [False] * 9, mask
        np.testing.assert_allclose(uv, [[0, 0], [7, 2]])
        np.testing.assert_allclose(depth, [1, 1])
        for rejected in (np.empty((0, 3)), points[2:]):
            uv, depth, mask = cam_to_image(rejected, p2, (4, 8))
            assert uv.shape == (0, 2) and depth.shape == (0,)
            assert mask.shape == (len(rejected),) and not mask.any()
        zero_scale = p2.copy()
        zero_scale[2] = 0
        uv, depth, mask = cam_to_image(points[:2], zero_scale, (4, 8))
        assert not mask.any() and uv.shape == (0, 2)
        interleaved = np.array([[np.inf, 0, 1], [7, 2, 1], [0, 0, -1], [0, 0, 2]])
        uv, depth, mask = cam_to_image(interleaved, p2, (4, 8))
        assert mask.tolist() == [False, True, False, True], mask
        np.testing.assert_allclose(uv, [[7, 2], [0, 0]])
        np.testing.assert_allclose(depth, [1, 2])
        invalid_cam = velo_to_cam(np.array([[np.inf, 0, 0]]), fr["calib"])
        assert not cam_to_image(invalid_cam, fr["calib"].P2, fr["image"].shape)[2].any()
    assert velo_to_cam(np.empty((0, 3)), fr["calib"]).shape == (0, 3)

    for root, frame, total, inside in (
        ("data/synthetic", "000000", 23953, 3910),
        ("data/kitti_mini", "000011", 108004, 19946),
        ("data/nuscenes_mini_subset", "scene-0103_010", 34720, 3120),
    ):
        fr = load_frame(root, frame)
        cam = velo_to_cam(fr["points"][:, :3], fr["calib"])
        uv, depth, mask = cam_to_image(cam, fr["calib"].P2, fr["image"].shape)
        assert len(mask) == total and int(mask.sum()) == inside, (frame, len(mask), mask.sum())
        assert len(uv) == len(depth) == inside and np.isfinite(uv).all()
        print(f"{root}/{frame}: points={total} inside_image={inside} [PASS]")
    print("CP2 self-test passed")


if __name__ == "__main__":
    main()
