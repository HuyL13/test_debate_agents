# Kết quả bàn giao

Code baseline đã triển khai; benchmark API thật **chưa chạy** vì chưa có key/model được cấu hình. Không có điểm PARD-adapted thật để so với paper.

| Split | Articles | Detection samples | Classification samples | Negatives |
|---|---:|---:|---:|---:|
| Train | 452 | 5,370 | 3,168 | 2,202 |
| Dev | 129 | 1,538 | 927 | 611 |
| Test | 67 | 798 | 481 | 317 |

Không trùng article hoặc comment ID giữa split. Một parent tham chiếu sai article/split đã được giữ nguyên dữ liệu và xử lý thành context rỗng: `399:10493`.

## Kiểm chứng

- Kiểm thử: xem `verification.json` để biết lệnh, số test và trạng thái đã chạy.
- Smoke matrix: `smoke_results.json` ghi 12 run, gồm sáu setting × hai task, mỗi run 10 mẫu dev. Dùng mock transport, không gọi API dịch vụ.
- JSON metric sinh trong `outputs/` là **synthetic**, chỉ để kiểm tra luồng và evaluator.
- Bộ kiểm thử bao gồm label leakage, filtering, metric, protocol budget, retry, raw audit, usage, cache, freeze, resume, coverage và corrupt manifest/log.

## Bảng thí nghiệm cần điền sau khi chạy API

| Method | Detection F1 (798 mẫu) | Classification Macro-F1 (481 mẫu) |
|---|---|---|
| Single API, cùng model/context | Chưa đo | Chưa đo |
| Three roles, no deliberation | Chưa đo | Chưa đo |
| Fixed Round-Robin | Chưa đo | Chưa đo |
| Fixed Point-Counterpoint | Chưa đo | Chưa đo |
| Fixed Cross-Examination | Chưa đo | Chưa đo |
| Adaptive PARD-inspired API | Chưa đo | Chưa đo |

Sau khi sửa model/key và kiểm tra dev, dùng các lệnh freeze/test trong README. Chỉ đối chiếu bảng paper khi split, filtering, labels, metric và context phù hợp; xem các giới hạn đã ghi trong `docs/UPSTREAM_AUDIT.md`.
