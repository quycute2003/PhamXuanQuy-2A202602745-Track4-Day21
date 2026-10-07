# Báo cáo Day 6: Độ nhạy của phép chiếu LiDAR-camera với lệch yaw

> Thay **mọi** ô có chữ ĐIỀN nằm trong ngoặc vuông bằng nội dung của bạn, xoá luôn cả dấu ngoặc vuông. Lệnh `python tools/check_submission.py` sẽ báo FAIL nếu còn sót bất kỳ chỗ nào.

- **Họ tên:** Phạm Xuân Quý
- **MSSV:** 2A202602745
- **Lớp:** [ĐIỀN]
- **Link repo:** https://github.com/quycute2003/PhamXuanQuy-2A202602745-Track4-Day21
- **Topic:** A — LiDAR-camera projection QA
- **Dataset:** data/kitti_mini (thí nghiệm chính); data/synthetic (debug); data/nuscenes_mini_subset (kiểm tra phép chiếu ở CP2).
- **Các frame đã dùng:** KITTI 000019 (vật gần), 000011 (người đi bộ), 000004 (xe xa), 000049 (che khuất); synthetic 000000; nuScenes scene-0103_010.

> Hãy viết ngắn: mỗi mục từ 3 đến 8 dòng, ưu tiên số liệu và hình ảnh.

## 1. Claim

**Claim đã kiểm chứng ở CP3:** Trên 26 vật thể Car/Pedestrian của 4 frame KITTI 000019, 000011, 000004 và 000049, lệch yaw +2° quanh trục z của LiDAR làm tỉ lệ điểm chiếu đúng vào 2D box tương ứng, trung bình đều theo vật thể, giảm từ **94.79% xuống 61.91%**, tức **32.88 điểm phần trăm**. Kết quả ủng hộ giả thuyết CP1 “giảm ít nhất 10 điểm phần trăm” trên mẫu đã chọn.

**Thí nghiệm:** Quét yaw 0°, +0.5°, +1°, +2°, +3°; giữ nguyên frame, điểm đầu vào, class Car/Pedestrian, translation và các góc khác; không giới hạn range và không dùng phép ngẫu nhiên. Đo thêm % điểm toàn frame nằm trong FOV, tách kết quả theo class và khoảng cách mặt phẳng camera `sqrt(x² + z²)`.

**Định nghĩa metric:** Chọn cố định các điểm hữu hạn nằm trong 3D box GT bằng calibration gốc; với mỗi vật thể có điểm, chia số điểm chiếu đúng vào 2D box của chính vật thể đó cho tổng số điểm đã chọn. Điểm ra ngoài ảnh hoặc sau camera vẫn nằm trong mẫu số và được tính là không khớp; lấy trung bình đều theo vật thể, bỏ DontCare và box không có điểm.

**Phạm vi:** Kết luận áp dụng cho 4 frame và yaw dương đã đo; chưa suy rộng cho toàn KITTI hoặc sensor khác. Label 2D/3D, truncation và occlusion ảnh hưởng baseline, nên không giả định calibration gốc luôn đạt 100%.

## 2. Evidence

**Benchmark CP3:** 4 frame × 5 mức yaw = 20 cấu hình; 26 vật thể (20 Car, 6 Pedestrian), không có box rỗng. Tập điểm GT và mẫu số của từng vật thể cố định ở cả 5 mức; tổng 9459 lượt điểm trong các box. Chạy hai lần, cả 4 CSV giống nhau từng byte.

| Yaw | Khớp box trung bình theo vật thể | Giảm so với 0° (điểm phần trăm) | Điểm toàn frame trong FOV |
|---|---|---|---|
| 0° | 94.79% | 0.00 | 16.740% |
| +0.5° | 88.08% | 6.70 | 16.755% |
| +1° | 76.98% | 17.81 | 16.767% |
| +2° | 61.91% | 32.88 | 16.781% |
| +3° | 45.63% | 49.16 | 16.781% |

![Yaw sweep: theo frame, class, khoảng cách và FOV](../results/figures/yaw_sweep.png)

Ở +2°, Car giảm **94.69% → 72.65%** (22.05 điểm phần trăm), Pedestrian giảm **95.09% → 26.12%** (68.97 điểm phần trăm): người đi bộ nhạy hơn trong mẫu này. Nhóm trên 30 m (8 vật thể) giảm **98.51% → 49.29%**, nhóm dưới 15 m (8 vật thể) giảm **86.10% → 66.00%**; đây là mô tả theo nhóm, chưa tách ảnh hưởng class/truncation khỏi khoảng cách.

FOV thay đổi chỉ **+0.041 điểm phần trăm** ở +2° dù mức khớp box giảm **32.88 điểm phần trăm**, nên FOV đơn lẻ không đủ để phát hiện drift trong thí nghiệm này. Baseline khớp box cố định là **94.79%**, khác **99.40%** của metric gộp chỉ tính điểm còn trong ảnh; ví dụ Car trong frame 000011 bị truncation 0.98. Không loại điểm ngoài FOV khỏi mẫu số để tránh che mất lỗi projection.

File: `results/yaw_perturb_sweep.csv` (20 dòng theo frame), `results/yaw_perturb_sweep_objects.csv` (130 dòng theo vật thể), `results/yaw_perturb_sweep_groups.csv` (25 dòng theo class/range), `results/yaw_perturb_sweep_summary.csv` (5 dòng tổng hợp). `mean_hit_ratio` là metric của claim; `pooled_hit_ratio` gộp theo số điểm; `visible_hit_ratio` là metric tham chiếu của script mẫu. Self-test CP3 khớp đủ 15 số tham chiếu trên 000008/000011/000049 với class Car/Van/Pedestrian/Cyclist, kiểm tra box xoay, mẫu số cố định và cách lấy trung bình.

**Demo CP2:** Self-test và 7 overlay đã chạy; số điểm trong ảnh của ba ca chuẩn là 3910 / 19946 / 3120, khớp hướng dẫn. Frame 000008 chỉ dùng đối chiếu script mẫu trong self-test CP3, không nằm trong benchmark 4 frame của claim.

![KITTI: vật gần, frame 000019](../results/figures/overlay_000019_r0.0_p0.0_y0.0_t0.0_0.0_0.0.png)
![KITTI: người đi bộ, frame 000011](../results/figures/overlay_000011_r0.0_p0.0_y0.0_t0.0_0.0_0.0.png)
![KITTI: xe xa, frame 000004](../results/figures/overlay_000004_r0.0_p0.0_y0.0_t0.0_0.0_0.0.png)

Nguồn ảnh: KITTI Vision Benchmark Suite; ảnh kiểm tra bổ sung từ nuScenes (Motional). Các ảnh còn lại nằm trong `results/figures/`, tái tạo bằng các lệnh ở mục 5. Quan sát synthetic yaw +2°: điểm trượt ngang khỏi cột và mép xe, nhưng FOV chỉ thay đổi từ 16.3% lên 16.5%; vì vậy FOV đơn lẻ chưa đủ để đánh giá calibration.

## 3. Failure case

Nêu khi nào hệ thống hoặc phương pháp fail, vì sao fail, và liên hệ tới lớp nào trong 6 lớp debug: I/O, Geometry, Time, Preprocess, Model, Metric.

![failure](../results/figures/fail_[ĐIỀN].png)

[ĐIỀN]

## 4. Khuyến nghị nếu triển khai thật

Use-case cụ thể (ADAS / robot / drone), trade-off và bước tiếp theo.

[ĐIỀN]

## 5. Cách chạy lại

Chạy từ thư mục gốc repo bằng Windows PowerShell, Python 3.11. Dùng trực tiếp Python trong `.venv` để không phụ thuộc việc kích hoạt môi trường hay execution policy; `-X utf8` tránh lỗi đọc tiếng Việt trên Windows.

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -X utf8 -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -X utf8 tools/verify_data.py --data-root data/kitti_mini
.\.venv\Scripts\python.exe -X utf8 tools/verify_data.py --data-root data/nuscenes_mini_subset
.\.venv\Scripts\python.exe -X utf8 -m src.test_projection
.\.venv\Scripts\python.exe -X utf8 -m starter.projection --data-root data/synthetic --frame 000000
.\.venv\Scripts\python.exe -X utf8 -m starter.projection --data-root data/synthetic --frame 000000 --yaw-deg 2
.\.venv\Scripts\python.exe -X utf8 -m starter.projection --data-root data/kitti_mini --frame 000019
.\.venv\Scripts\python.exe -X utf8 -m starter.projection --data-root data/kitti_mini --frame 000011
.\.venv\Scripts\python.exe -X utf8 -m starter.projection --data-root data/kitti_mini --frame 000004
.\.venv\Scripts\python.exe -X utf8 -m starter.projection --data-root data/kitti_mini --frame 000049
.\.venv\Scripts\python.exe -X utf8 -m starter.projection --data-root data/nuscenes_mini_subset --frame scene-0103_010
.\.venv\Scripts\python.exe -X utf8 -m src.test_yaw_sweep
.\.venv\Scripts\python.exe -X utf8 -m src.exp_yaw_sweep --data-root data/kitti_mini --frames 000019 000011 000004 000049 --classes Car Pedestrian --yaw-levels 0 0.5 1 2 3
.\.venv\Scripts\python.exe -X utf8 -m src.plot_yaw_sweep
```

Self-test phải in `CP2 self-test passed`; hai lệnh kiểm tra dữ liệu phải in `[PASS]`. Self-test kiểm tra điểm chuẩn, NaN/Inf, điểm sau camera, ngoài FOV, ngưỡng depth, biên ảnh, input rỗng, mẫu số chiếu bằng 0 và thứ tự mask/depth. Ảnh overlay được lưu trong `results/figures/`; nuScenes dùng bù ego-motion mặc định.

Tự kiểm tra tái lập CP3 (cùng frame/class/mức yaw mặc định như lệnh benchmark trên):

```powershell
.\.venv\Scripts\python.exe -X utf8 -m src.exp_yaw_sweep --out results/check_rerun.csv
@'
import filecmp
for suffix in ('', '_objects', '_groups', '_summary'):
    assert filecmp.cmp(f'results/yaw_perturb_sweep{suffix}.csv', f'results/check_rerun{suffix}.csv', shallow=False), suffix
print('All 4 CSV files are byte-identical')
'@ | .\.venv\Scripts\python.exe -X utf8 -
Remove-Item -LiteralPath results\check_rerun.csv, results\check_rerun_objects.csv, results\check_rerun_groups.csv, results\check_rerun_summary.csv
```

`src.test_yaw_sweep` phải in `CP3 metric self-test passed`. Hai script thí nghiệm/vẽ có `--help` để đổi dataset, frame, class, mức yaw hoặc đường dẫn kết quả. Không có phép ngẫu nhiên nên không cần seed. Kết quả tái lập không bao gồm thời gian chạy hoặc metadata PNG.

## 6. Khai báo sử dụng AI

Ghi rõ đã dùng công cụ AI nào, dùng vào việc gì, và bạn đã tự kiểm chứng kết quả đó bằng cách nào. Nếu không dùng AI, ghi "Không sử dụng". Xem quy định ở `RULES.md` mục 2.

| Công cụ | Dùng cho việc gì | Bạn đã kiểm chứng thế nào |
|---|---|---|
| Codex (OpenAI) | Đọc yêu cầu CP0–CP3, đề xuất claim, viết phép chiếu/self-test, cài môi trường, chạy demo/benchmark, vẽ biểu đồ và viết báo cáo. Dùng script mẫu CP3 làm điểm xuất phát, mở rộng mẫu số cố định, trung bình đều theo vật thể, tách class/range, lưu chi tiết từng vật thể và metric tham chiếu | Codex đã kiểm tra checksum, tự kiểm bằng số/ca biên, đối chiếu 3 số FOV và 15 tỉ lệ của đề, xem ảnh/biểu đồ; chạy benchmark hai lần cho 4 CSV giống từng byte và đối chiếu tổng hợp với dữ liệu từng vật thể. Học viên chưa xác nhận tự kiểm chứng; cần tự chạy lại và giải thích code, metric, số liệu trước khi nộp. |
