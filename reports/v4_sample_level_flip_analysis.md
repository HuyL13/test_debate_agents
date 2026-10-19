# BÁO CÁO KẾT QUẢ ĐỐI KHÁNG 3-AGENT (V4) - 66 MẪU HARD ERRORS

## 1. TỔNG QUAN HIỆU NĂNG V4 VS V3

| Chỉ số | Single Agent (Prosecutor) | Debate V3 (Baseline) | Debate V4 (Có Cue + Unanimous Burden) | Chênh lệch V4 vs V3 |
| :--- | :---: | :---: | :---: | :---: |
| **Độ chính xác (Accuracy)** | 26/66 (39.39%) | 24/66 (36.36%) | **28/66 (42.42%)** | **+6.06% (+4 mẫu)** |
| **Macro-F1** | - | 31.24% | **38.11%** | **+6.87%** |
| **Ca lật có hại (Harmful Flips)** | - | 12 ca (phá hỏng kết quả) | **0 ca (0.0%)** | **-12 ca (Triệt tiêu 100%)** |
| **Ca lật có lợi (Beneficial Flips)** | - | 10 ca | **2 ca** | -8 ca |
| **Tỷ lệ bảo vệ mẫu đúng của Prosecutor** | 100% | 14/26 (53.8%) | **26/26 (100.0%)** | **+46.2%** |

---

## 2. PHÂN BỐ LẬT NHÃN (FLIP AUDIT MATRIX)

### Nhóm 1: 26 ca Prosecutor ban đầu ĐÚNG
- **Giữ Đúng (Protected / Upheld): 26 / 26 (100.0%)**
  - 23 ca: Defender chủ động **Concede** (`alternative_class: None`) do học được phân bố few-shot cân bằng.
  - 3 ca: Defender thách thức nhưng Arbiter chạy kiểm định đối xứng 2 chiều (Order-Permuted Consensus) và quy tắc Cue khóa (Cue Locking) -> Arbiter bác bỏ thách thức và bảo vệ Candidate thành công (`617:11147`, `168:5000`, `323:6965`).
- **Lật Sai (Harmful Flips): 0 / 26 (0.0%)** (Ở V3 bị mất tới 12 ca, V4 giữ trọn vẹn 100%).

### Nhóm 2: 40 ca Prosecutor ban đầu SAI
- **Lật Đúng (Beneficial Flips): 2 ca**
  - `287:5658`: Gold = `Appeal to Majority` (Prosecutor đoán `Appeal to Nature` -> Defender phản biện `Appeal to Majority` -> Arbiter đồng thuận lật).
  - `162:4982`: Gold = `Hasty Generalization` (Prosecutor đoán `Appeal to Tradition` -> Defender phản biện `Hasty Generalization` -> Arbiter đồng thuận lật).
- **Lật sang Sai khác: 0 ca**
- **Giữ nguyên Sai: 38 ca** (Defender concede hoặc Challenger không đủ bằng chứng vượt qua Burden of Proof).

---

## 3. BẢNG CHI TIẾT 66 MẪU (FULL AUDIT TABLE)

| STT | Sample ID | Gold | Prosecutor Candidate | Defender Alternative | Final V4 | Phân loại Lật nhãn |
| :---: | :---: | :--- | :--- | :--- | :--- | :--- |
| 1 | `427:6079` | **Appeal to Authority** | Appeal to Authority | None | **Appeal to Authority** | Prosecutor Đúng -> Giữ Đúng (Protected) |
| 2 | `347:6437` | **Slippery Slope** | Appeal to Worse Problems | None | **Appeal to Worse Problems** | Prosecutor Sai -> Giữ nguyên Sai |
| 3 | `19:9353` | **Appeal to Tradition** | Appeal to Tradition | None | **Appeal to Tradition** | Prosecutor Đúng -> Giữ Đúng (Protected) |
| 4 | `599:7794` | **Appeal to Worse Problems** | Slippery Slope | None | **Slippery Slope** | Prosecutor Sai -> Giữ nguyên Sai |
| 5 | `5:3163` | **Appeal to Tradition** | Appeal to Tradition | None | **Appeal to Tradition** | Prosecutor Đúng -> Giữ Đúng (Protected) |
| 6 | `486:8056` | **Slippery Slope** | Appeal to Worse Problems | None | **Appeal to Worse Problems** | Prosecutor Sai -> Giữ nguyên Sai |
| 7 | `208:5120` | **Slippery Slope** | Appeal to Tradition | None | **Appeal to Tradition** | Prosecutor Sai -> Giữ nguyên Sai |
| 8 | `146:4635` | **Appeal to Authority** | Appeal to Authority | None | **Appeal to Authority** | Prosecutor Đúng -> Giữ Đúng (Protected) |
| 9 | `621:7859` | **Appeal to Authority** | Appeal to Nature | None | **Appeal to Nature** | Prosecutor Sai -> Giữ nguyên Sai |
| 10 | `621:7861` | **Hasty Generalization** | Appeal to Nature | None | **Appeal to Nature** | Prosecutor Sai -> Giữ nguyên Sai |
| 11 | `621:9060` | **False Dilemma** | Slippery Slope | None | **Slippery Slope** | Prosecutor Sai -> Giữ nguyên Sai |
| 12 | `465:10692` | **Slippery Slope** | Slippery Slope | None | **Slippery Slope** | Prosecutor Đúng -> Giữ Đúng (Protected) |
| 13 | `409:7223` | **Appeal to Tradition** | Appeal to Tradition | None | **Appeal to Tradition** | Prosecutor Đúng -> Giữ Đúng (Protected) |
| 14 | `355:5861` | **False Dilemma** | Appeal to Nature | None | **Appeal to Nature** | Prosecutor Sai -> Giữ nguyên Sai |
| 15 | `355:5863` | **Appeal to Authority** | Appeal to Authority | None | **Appeal to Authority** | Prosecutor Đúng -> Giữ Đúng (Protected) |
| 16 | `489:7464` | **False Dilemma** | Slippery Slope | None | **Slippery Slope** | Prosecutor Sai -> Giữ nguyên Sai |
| 17 | `538:8211` | **Hasty Generalization** | Appeal to Nature | None | **Appeal to Nature** | Prosecutor Sai -> Giữ nguyên Sai |
| 18 | `538:10911` | **Hasty Generalization** | Slippery Slope | None | **Slippery Slope** | Prosecutor Sai -> Giữ nguyên Sai |
| 19 | `20:3058` | **Appeal to Worse Problems** | Appeal to Worse Problems | None | **Appeal to Worse Problems** | Prosecutor Đúng -> Giữ Đúng (Protected) |
| 20 | `20:3057` | **Hasty Generalization** | Appeal to Tradition | None | **Appeal to Tradition** | Prosecutor Sai -> Giữ nguyên Sai |
| 21 | `239:4913` | **Slippery Slope** | Slippery Slope | None | **Slippery Slope** | Prosecutor Đúng -> Giữ Đúng (Protected) |
| 22 | `239:4915` | **Appeal to Tradition** | Appeal to Nature | None | **Appeal to Nature** | Prosecutor Sai -> Giữ nguyên Sai |
| 23 | `239:5213` | **Appeal to Worse Problems** | Appeal to Worse Problems | None | **Appeal to Worse Problems** | Prosecutor Đúng -> Giữ Đúng (Protected) |
| 24 | `239:5514` | **Hasty Generalization** | Appeal to Authority | None | **Appeal to Authority** | Prosecutor Sai -> Giữ nguyên Sai |
| 25 | `239:10013` | **Appeal to Tradition** | Appeal to Majority | None | **Appeal to Majority** | Prosecutor Sai -> Giữ nguyên Sai |
| 26 | `22:3064` | **Appeal to Worse Problems** | Appeal to Nature | None | **Appeal to Nature** | Prosecutor Sai -> Giữ nguyên Sai |
| 27 | `22:3212` | **Slippery Slope** | Appeal to Worse Problems | None | **Appeal to Worse Problems** | Prosecutor Sai -> Giữ nguyên Sai |
| 28 | `22:3962` | **Hasty Generalization** | False Dilemma | None | **False Dilemma** | Prosecutor Sai -> Giữ nguyên Sai |
| 29 | `22:3963` | **Appeal to Worse Problems** | Appeal to Majority | None | **Appeal to Majority** | Prosecutor Sai -> Giữ nguyên Sai |
| 30 | `133:3846` | **Slippery Slope** | Hasty Generalization | None | **Hasty Generalization** | Prosecutor Sai -> Giữ nguyên Sai |
| 31 | `304:6908` | **False Dilemma** | Appeal to Tradition | None | **Appeal to Tradition** | Prosecutor Sai -> Giữ nguyên Sai |
| 32 | `442:6123` | **Slippery Slope** | Appeal to Authority | None | **Appeal to Authority** | Prosecutor Sai -> Giữ nguyên Sai |
| 33 | `66:4095` | **Hasty Generalization** | Appeal to Authority | None | **Appeal to Authority** | Prosecutor Sai -> Giữ nguyên Sai |
| 34 | `386:5955` | **Slippery Slope** | Appeal to Tradition | None | **Appeal to Tradition** | Prosecutor Sai -> Giữ nguyên Sai |
| 35 | `386:7155` | **Hasty Generalization** | Appeal to Authority | False Dilemma | **Appeal to Authority** | Prosecutor Sai -> Giữ nguyên Sai |
| 36 | `386:10455` | **Appeal to Nature** | Appeal to Nature | None | **Appeal to Nature** | Prosecutor Đúng -> Giữ Đúng (Protected) |
| 37 | `589:7765` | **Slippery Slope** | Appeal to Worse Problems | None | **Appeal to Worse Problems** | Prosecutor Sai -> Giữ nguyên Sai |
| 38 | `313:6336` | **Appeal to Nature** | Appeal to Nature | None | **Appeal to Nature** | Prosecutor Đúng -> Giữ Đúng (Protected) |
| 39 | `359:5873` | **Appeal to Tradition** | Appeal to Nature | None | **Appeal to Nature** | Prosecutor Sai -> Giữ nguyên Sai |
| 40 | `58:3621` | **False Dilemma** | Appeal to Tradition | None | **Appeal to Tradition** | Prosecutor Sai -> Giữ nguyên Sai |
| 41 | `164:9790` | **Hasty Generalization** | Appeal to Nature | Appeal to Authority | **Appeal to Nature** | Prosecutor Sai -> Giữ nguyên Sai |
| 42 | `192:5072` | **False Dilemma** | Appeal to Tradition | None | **Appeal to Tradition** | Prosecutor Sai -> Giữ nguyên Sai |
| 43 | `296:10185` | **Hasty Generalization** | Appeal to Worse Problems | None | **Appeal to Worse Problems** | Prosecutor Sai -> Giữ nguyên Sai |
| 44 | `645:7932` | **Hasty Generalization** | Slippery Slope | None | **Slippery Slope** | Prosecutor Sai -> Giữ nguyên Sai |
| 45 | `645:8532` | **Hasty Generalization** | Appeal to Worse Problems | None | **Appeal to Worse Problems** | Prosecutor Sai -> Giữ nguyên Sai |
| 46 | `617:11147` | **Appeal to Authority** | Appeal to Authority | Slippery Slope | **Appeal to Authority** | Prosecutor Đúng -> Giữ Đúng (Protected) |
| 47 | `429:6685` | **Appeal to Majority** | Appeal to Majority | None | **Appeal to Majority** | Prosecutor Đúng -> Giữ Đúng (Protected) |
| 48 | `287:5658` | **Appeal to Majority** | Appeal to Nature | Appeal to Majority | **Appeal to Majority** | Prosecutor Sai -> Lật Đúng (Beneficial Flip) |
| 49 | `287:6859` | **Appeal to Authority** | Appeal to Authority | None | **Appeal to Authority** | Prosecutor Đúng -> Giữ Đúng (Protected) |
| 50 | `287:10158` | **Appeal to Nature** | Appeal to Worse Problems | None | **Appeal to Worse Problems** | Prosecutor Sai -> Giữ nguyên Sai |
| 51 | `168:5000` | **Appeal to Worse Problems** | Appeal to Worse Problems | Slippery Slope | **Appeal to Worse Problems** | Prosecutor Đúng -> Giữ Đúng (Protected) |
| 52 | `595:7783` | **Appeal to Worse Problems** | Slippery Slope | None | **Slippery Slope** | Prosecutor Sai -> Giữ nguyên Sai |
| 53 | `2:3904` | **Appeal to Majority** | Appeal to Tradition | None | **Appeal to Tradition** | Prosecutor Sai -> Giữ nguyên Sai |
| 54 | `433:6696` | **Appeal to Worse Problems** | Appeal to Worse Problems | None | **Appeal to Worse Problems** | Prosecutor Đúng -> Giữ Đúng (Protected) |
| 55 | `323:6965` | **Appeal to Tradition** | Appeal to Tradition | Appeal to Nature | **Appeal to Tradition** | Prosecutor Đúng -> Giữ Đúng (Protected) |
| 56 | `162:4982` | **Hasty Generalization** | Appeal to Tradition | Hasty Generalization | **Hasty Generalization** | Prosecutor Sai -> Lật Đúng (Beneficial Flip) |
| 57 | `162:9784` | **Appeal to Worse Problems** | Appeal to Worse Problems | None | **Appeal to Worse Problems** | Prosecutor Đúng -> Giữ Đúng (Protected) |
| 58 | `399:7193` | **Slippery Slope** | Slippery Slope | None | **Slippery Slope** | Prosecutor Đúng -> Giữ Đúng (Protected) |
| 59 | `1:3900` | **Hasty Generalization** | Appeal to Authority | None | **Appeal to Authority** | Prosecutor Sai -> Giữ nguyên Sai |
| 60 | `335:5802` | **Slippery Slope** | Slippery Slope | None | **Slippery Slope** | Prosecutor Đúng -> Giữ Đúng (Protected) |
| 61 | `335:7003` | **Hasty Generalization** | Appeal to Majority | None | **Appeal to Majority** | Prosecutor Sai -> Giữ nguyên Sai |
| 62 | `335:7002` | **Appeal to Authority** | Appeal to Authority | None | **Appeal to Authority** | Prosecutor Đúng -> Giữ Đúng (Protected) |
| 63 | `387:5959` | **Appeal to Worse Problems** | Appeal to Worse Problems | None | **Appeal to Worse Problems** | Prosecutor Đúng -> Giữ Đúng (Protected) |
| 64 | `416:6044` | **Appeal to Authority** | Appeal to Authority | None | **Appeal to Authority** | Prosecutor Đúng -> Giữ Đúng (Protected) |
| 65 | `416:6644` | **Appeal to Worse Problems** | Appeal to Worse Problems | None | **Appeal to Worse Problems** | Prosecutor Đúng -> Giữ Đúng (Protected) |
| 66 | `87:3709` | **Appeal to Tradition** | Appeal to Tradition | None | **Appeal to Tradition** | Prosecutor Đúng -> Giữ Đúng (Protected) |