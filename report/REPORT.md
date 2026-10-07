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

**Claim nháp (giả thuyết CP1, chưa có số liệu):** Trên 4 frame KITTI 000019, 000011, 000004 và 000049, lệch yaw +2° quanh trục z của LiDAR làm tỉ lệ điểm của vật thể chiếu đúng vào 2D box tương ứng, trung bình theo vật thể Car/Pedestrian, giảm ít nhất 10 điểm phần trăm so với calibration gốc.

**Kế hoạch đo:** Quét yaw 0°, +0.5°, +1°, +2°, +3°; giữ nguyên frame, điểm đầu vào, class, translation và các góc khác. Đo thêm % điểm toàn frame nằm trong FOV.

**Định nghĩa metric:** Chọn cố định các điểm hữu hạn nằm trong 3D box GT bằng calibration gốc; với mỗi vật thể có điểm, chia số điểm chiếu đúng vào 2D box của chính vật thể đó cho tổng số điểm đã chọn. Điểm ra ngoài ảnh hoặc sau camera vẫn nằm trong mẫu số và được tính là không khớp; lấy trung bình đều theo vật thể, bỏ DontCare và box không có điểm.

**Tiêu chí kết luận:** Claim được ủng hộ nếu chênh lệch giữa yaw 0° và +2° đạt ít nhất 10 điểm phần trăm; nếu không, báo cáo số đo thực tế và bác bỏ hoặc sửa claim ở CP3.

## 2. Evidence

**Demo CP2:** Đã chạy self-test và 7 lệnh overlay. Ba ca chuẩn khớp đúng số điểm trong ảnh của hướng dẫn; benchmark tỉ lệ điểm khớp box để kiểm chứng claim sẽ thực hiện ở CP3.

| Dataset / frame | Yaw | Tổng điểm | Điểm trong FOV | Tỉ lệ FOV |
|---|---|---|---|---|
| synthetic / 000000 | 0° | 23953 | 3910 | 16.3% |
| synthetic / 000000 | +2° | 23953 | 3956 | 16.5% |
| KITTI / 000019 | 0° | 115697 | 18792 | 16.2% |
| KITTI / 000011 | 0° | 108004 | 19946 | 18.5% |
| KITTI / 000004 | 0° | 115976 | 19063 | 16.4% |
| KITTI / 000049 | 0° | 113691 | 18093 | 15.9% |
| nuScenes / scene-0103_010 | 0° | 34720 | 3120 | 9.0% |

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
```

Self-test phải in `CP2 self-test passed`; hai lệnh kiểm tra dữ liệu phải in `[PASS]`. Self-test kiểm tra điểm chuẩn, NaN/Inf, điểm sau camera, ngoài FOV, ngưỡng depth, biên ảnh, input rỗng, mẫu số chiếu bằng 0 và thứ tự mask/depth. Ảnh overlay được lưu trong `results/figures/`; nuScenes dùng bù ego-motion mặc định.

## 6. Khai báo sử dụng AI

Ghi rõ đã dùng công cụ AI nào, dùng vào việc gì, và bạn đã tự kiểm chứng kết quả đó bằng cách nào. Nếu không dùng AI, ghi "Không sử dụng". Xem quy định ở `RULES.md` mục 2.

| Công cụ | Dùng cho việc gì | Bạn đã kiểm chứng thế nào |
|---|---|---|
| Codex (OpenAI) | Đọc yêu cầu CP0–CP2, điền thông tin, đề xuất topic/frame/claim; viết 2 hàm TODO và self-test; cài môi trường, chạy demo và cập nhật báo cáo | Codex đã chạy kiểm tra checksum hai dataset, self-test bằng số và ca biên, đối chiếu 3910/19946/3120 điểm trong FOV với đề, xem 7 ảnh overlay. Học viên chưa xác nhận tự kiểm chứng; cần tự chạy lại, giải thích phép chiếu và kiểm chứng claim bằng benchmark ở CP3. |
