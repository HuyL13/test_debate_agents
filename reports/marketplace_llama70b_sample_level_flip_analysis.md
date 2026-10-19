# BÁO CÁO KẾT QUẢ ĐỐI KHÁNG 3-AGENT: LLAMA-3.3-70B-INSTRUCT (MARKETPLACE)

## 1. TỔNG QUAN HIỆU NĂNG: LLAMA-3.3-70B VS LLAMA-3.2-11B VS GPT-OSS-120B

| Chỉ số | Llama-3.3-70B (Marketplace) | Llama-3.2-11B V4 (NVIDIA) | GPT-OSS-120B (Marketplace) | Llama-3.2-11B V3 (Baseline) |
| :--- | :---: | :---: | :---: | :---: |
| **Độ chính xác (Accuracy)** | **34/66 (51.52%)** | 28/66 (42.42%) | 25/66 (37.88%) | 24/66 (36.36%) |
| **Macro-F1** | **48.60%** | 38.11% | 35.96% | 31.24% |
| **Ca lật có hại (Harmful Flips)** | **0 ca (0.0%)** | 0 ca (0.0%) | 0 ca (0.0%) | 12 ca |
| **Ca lật có lợi (Beneficial Flips)** | **0 ca** | 2 ca | 1 ca | 10 ca |
| **Tỷ lệ bảo vệ mẫu đúng** | **34/34 (100.0%)** | 26/26 (100.0%) | 24/24 (100.0%) | 14/26 (53.8%) |

---

## 2. BẢNG CHI TIẾT 66 MẪU (FULL AUDIT TABLE)

| STT | Sample ID | Gold | Prosecutor Candidate | Defender Alternative | Final Prediction | Phân loại Lật nhãn |
| :---: | :---: | :--- | :--- | :--- | :--- | :--- |
| 1 | `427:6079` | **Appeal to Authority** | Appeal to Authority | None | **Appeal to Authority** | Prosecutor Đúng -> Giữ Đúng (Protected) |
| 2 | `347:6437` | **Slippery Slope** | Slippery Slope | None | **Slippery Slope** | Prosecutor Đúng -> Giữ Đúng (Protected) |
| 3 | `19:9353` | **Appeal to Tradition** | Appeal to Tradition | None | **Appeal to Tradition** | Prosecutor Đúng -> Giữ Đúng (Protected) |
| 4 | `599:7794` | **Appeal to Worse Problems** | Slippery Slope | None | **Slippery Slope** | Prosecutor Sai -> Giữ nguyên Sai |
| 5 | `5:3163` | **Appeal to Tradition** | Appeal to Tradition | None | **Appeal to Tradition** | Prosecutor Đúng -> Giữ Đúng (Protected) |
| 6 | `486:8056` | **Slippery Slope** | Slippery Slope | None | **Slippery Slope** | Prosecutor Đúng -> Giữ Đúng (Protected) |
| 7 | `208:5120` | **Slippery Slope** | Slippery Slope | None | **Slippery Slope** | Prosecutor Đúng -> Giữ Đúng (Protected) |
| 8 | `146:4635` | **Appeal to Authority** | Slippery Slope | None | **Slippery Slope** | Prosecutor Sai -> Giữ nguyên Sai |
| 9 | `621:7859` | **Appeal to Authority** | Appeal to Authority | None | **Appeal to Authority** | Prosecutor Đúng -> Giữ Đúng (Protected) |
| 10 | `621:7861` | **Hasty Generalization** | Hasty Generalization | None | **Hasty Generalization** | Prosecutor Đúng -> Giữ Đúng (Protected) |
| 11 | `621:9060` | **False Dilemma** | Slippery Slope | None | **Slippery Slope** | Prosecutor Sai -> Giữ nguyên Sai |
| 12 | `465:10692` | **Slippery Slope** | Slippery Slope | None | **Slippery Slope** | Prosecutor Đúng -> Giữ Đúng (Protected) |
| 13 | `409:7223` | **Appeal to Tradition** | Hasty Generalization | None | **Hasty Generalization** | Prosecutor Sai -> Giữ nguyên Sai |
| 14 | `355:5861` | **False Dilemma** | Slippery Slope | None | **Slippery Slope** | Prosecutor Sai -> Giữ nguyên Sai |
| 15 | `355:5863` | **Appeal to Authority** | Appeal to Authority | None | **Appeal to Authority** | Prosecutor Đúng -> Giữ Đúng (Protected) |
| 16 | `489:7464` | **False Dilemma** | Slippery Slope | None | **Slippery Slope** | Prosecutor Sai -> Giữ nguyên Sai |
| 17 | `538:8211` | **Hasty Generalization** | Slippery Slope | None | **Slippery Slope** | Prosecutor Sai -> Giữ nguyên Sai |
| 18 | `538:10911` | **Hasty Generalization** | Slippery Slope | None | **Slippery Slope** | Prosecutor Sai -> Giữ nguyên Sai |
| 19 | `20:3058` | **Appeal to Worse Problems** | False Dilemma | Appeal to Authority | **Appeal to Authority** | Prosecutor Sai -> Lật sang Sai khác |
| 20 | `20:3057` | **Hasty Generalization** | False Dilemma | None | **False Dilemma** | Prosecutor Sai -> Giữ nguyên Sai |
| 21 | `239:4913` | **Slippery Slope** | Slippery Slope | None | **Slippery Slope** | Prosecutor Đúng -> Giữ Đúng (Protected) |
| 22 | `239:4915` | **Appeal to Tradition** | Appeal to Nature | None | **Appeal to Nature** | Prosecutor Sai -> Giữ nguyên Sai |
| 23 | `239:5213` | **Appeal to Worse Problems** | Appeal to Worse Problems | None | **Appeal to Worse Problems** | Prosecutor Đúng -> Giữ Đúng (Protected) |
| 24 | `239:5514` | **Hasty Generalization** | Slippery Slope | None | **Slippery Slope** | Prosecutor Sai -> Giữ nguyên Sai |
| 25 | `239:10013` | **Appeal to Tradition** | Appeal to Majority | None | **Appeal to Majority** | Prosecutor Sai -> Giữ nguyên Sai |
| 26 | `22:3064` | **Appeal to Worse Problems** | Slippery Slope | None | **Slippery Slope** | Prosecutor Sai -> Giữ nguyên Sai |
| 27 | `22:3212` | **Slippery Slope** | Slippery Slope | None | **Slippery Slope** | Prosecutor Đúng -> Giữ Đúng (Protected) |
| 28 | `22:3962` | **Hasty Generalization** | False Dilemma | None | **False Dilemma** | Prosecutor Sai -> Giữ nguyên Sai |
| 29 | `22:3963` | **Appeal to Worse Problems** | Appeal to Worse Problems | None | **Appeal to Worse Problems** | Prosecutor Đúng -> Giữ Đúng (Protected) |
| 30 | `133:3846` | **Slippery Slope** | Slippery Slope | None | **Slippery Slope** | Prosecutor Đúng -> Giữ Đúng (Protected) |
| 31 | `304:6908` | **False Dilemma** | False Dilemma | None | **False Dilemma** | Prosecutor Đúng -> Giữ Đúng (Protected) |
| 32 | `442:6123` | **Slippery Slope** | Slippery Slope | None | **Slippery Slope** | Prosecutor Đúng -> Giữ Đúng (Protected) |
| 33 | `66:4095` | **Hasty Generalization** | False Dilemma | None | **False Dilemma** | Prosecutor Sai -> Giữ nguyên Sai |
| 34 | `386:5955` | **Slippery Slope** | Slippery Slope | None | **Slippery Slope** | Prosecutor Đúng -> Giữ Đúng (Protected) |
| 35 | `386:7155` | **Hasty Generalization** | False Dilemma | None | **False Dilemma** | Prosecutor Sai -> Giữ nguyên Sai |
| 36 | `386:10455` | **Appeal to Nature** | Hasty Generalization | None | **Hasty Generalization** | Prosecutor Sai -> Giữ nguyên Sai |
| 37 | `589:7765` | **Slippery Slope** | Slippery Slope | None | **Slippery Slope** | Prosecutor Đúng -> Giữ Đúng (Protected) |
| 38 | `313:6336` | **Appeal to Nature** | Appeal to Nature | None | **Appeal to Nature** | Prosecutor Đúng -> Giữ Đúng (Protected) |
| 39 | `359:5873` | **Appeal to Tradition** | Appeal to Tradition | None | **Appeal to Tradition** | Prosecutor Đúng -> Giữ Đúng (Protected) |
| 40 | `58:3621` | **False Dilemma** | False Dilemma | None | **False Dilemma** | Prosecutor Đúng -> Giữ Đúng (Protected) |
| 41 | `164:9790` | **Hasty Generalization** | Hasty Generalization | None | **Hasty Generalization** | Prosecutor Đúng -> Giữ Đúng (Protected) |
| 42 | `192:5072` | **False Dilemma** | Slippery Slope | None | **Slippery Slope** | Prosecutor Sai -> Giữ nguyên Sai |
| 43 | `296:10185` | **Hasty Generalization** | Slippery Slope | None | **Slippery Slope** | Prosecutor Sai -> Giữ nguyên Sai |
| 44 | `645:7932` | **Hasty Generalization** | Slippery Slope | None | **Slippery Slope** | Prosecutor Sai -> Giữ nguyên Sai |
| 45 | `645:8532` | **Hasty Generalization** | False Dilemma | None | **False Dilemma** | Prosecutor Sai -> Giữ nguyên Sai |
| 46 | `617:11147` | **Appeal to Authority** | Slippery Slope | None | **Slippery Slope** | Prosecutor Sai -> Giữ nguyên Sai |
| 47 | `429:6685` | **Appeal to Majority** | Appeal to Majority | None | **Appeal to Majority** | Prosecutor Đúng -> Giữ Đúng (Protected) |
| 48 | `287:5658` | **Appeal to Majority** | Hasty Generalization | Appeal to Nature | **Appeal to Nature** | Prosecutor Sai -> Lật sang Sai khác |
| 49 | `287:6859` | **Appeal to Authority** | Appeal to Authority | None | **Appeal to Authority** | Prosecutor Đúng -> Giữ Đúng (Protected) |
| 50 | `287:10158` | **Appeal to Nature** | Appeal to Worse Problems | None | **Appeal to Worse Problems** | Prosecutor Sai -> Giữ nguyên Sai |
| 51 | `168:5000` | **Appeal to Worse Problems** | Slippery Slope | None | **Slippery Slope** | Prosecutor Sai -> Giữ nguyên Sai |
| 52 | `595:7783` | **Appeal to Worse Problems** | Slippery Slope | None | **Slippery Slope** | Prosecutor Sai -> Giữ nguyên Sai |
| 53 | `2:3904` | **Appeal to Majority** | False Dilemma | None | **False Dilemma** | Prosecutor Sai -> Giữ nguyên Sai |
| 54 | `433:6696` | **Appeal to Worse Problems** | Hasty Generalization | None | **Hasty Generalization** | Prosecutor Sai -> Giữ nguyên Sai |
| 55 | `323:6965` | **Appeal to Tradition** | Appeal to Tradition | None | **Appeal to Tradition** | Prosecutor Đúng -> Giữ Đúng (Protected) |
| 56 | `162:4982` | **Hasty Generalization** | Hasty Generalization | None | **Hasty Generalization** | Prosecutor Đúng -> Giữ Đúng (Protected) |
| 57 | `162:9784` | **Appeal to Worse Problems** | Slippery Slope | None | **Slippery Slope** | Prosecutor Sai -> Giữ nguyên Sai |
| 58 | `399:7193` | **Slippery Slope** | Slippery Slope | None | **Slippery Slope** | Prosecutor Đúng -> Giữ Đúng (Protected) |
| 59 | `1:3900` | **Hasty Generalization** | False Dilemma | None | **False Dilemma** | Prosecutor Sai -> Giữ nguyên Sai |
| 60 | `335:5802` | **Slippery Slope** | Slippery Slope | None | **Slippery Slope** | Prosecutor Đúng -> Giữ Đúng (Protected) |
| 61 | `335:7003` | **Hasty Generalization** | Appeal to Majority | None | **Appeal to Majority** | Prosecutor Sai -> Giữ nguyên Sai |
| 62 | `335:7002` | **Appeal to Authority** | Appeal to Authority | None | **Appeal to Authority** | Prosecutor Đúng -> Giữ Đúng (Protected) |
| 63 | `387:5959` | **Appeal to Worse Problems** | Appeal to Worse Problems | None | **Appeal to Worse Problems** | Prosecutor Đúng -> Giữ Đúng (Protected) |
| 64 | `416:6044` | **Appeal to Authority** | Appeal to Authority | None | **Appeal to Authority** | Prosecutor Đúng -> Giữ Đúng (Protected) |
| 65 | `416:6644` | **Appeal to Worse Problems** | Appeal to Worse Problems | None | **Appeal to Worse Problems** | Prosecutor Đúng -> Giữ Đúng (Protected) |
| 66 | `87:3709` | **Appeal to Tradition** | Appeal to Tradition | None | **Appeal to Tradition** | Prosecutor Đúng -> Giữ Đúng (Protected) |