# CoCoLoFa × PARD-inspired API baseline

Repo Python local thực hiện hai task gốc của CoCoLoFa với kiến trúc reasoning lấy cảm hứng từ PARD. Đây là **bản adaptation**, không phải reproduction đầy đủ của PARD.

- **Detection:** toàn bộ bình luận của split; output `Fallacious` / `Non-Fallacious`.
- **Classification:** chỉ gold-positive; chọn một trong tám nhãn; không cascade từ detection.
- Ba vai trò Factual / Logical / Contextual phân tích độc lập → planner chọn protocol → deliberation → arbiter tổng hợp.
- Cùng một model API cho mọi vai trò. Không model selection, RL, retrieval, tool calling hay feedback memory giữa các mẫu.

## Trạng thái bàn giao

**Full test single đang chạy; adaptive đã dừng theo yêu cầu:**
[bảng đối sánh với paper](reports/FULL_TEST_COMPARISON.md) tự cập nhật mỗi 30 giây.
Bốn cấu hình cũ đã đóng băng bằng `reports/frozen-full-*-v1.json`; target mỗi method
là 798/481 mẫu. Hai adaptive dừng giữa chừng, không có điểm full-test.
Chi tiết tiến độ và log ở `outputs/full-test-v1/status.json` và các file `.console.log`.
Giữ máy thức và có mạng. Supervisor cũ đã dừng; monitor hiện tại chỉ quan sát,
không tự khởi động lại adaptive. Bản runtime cũ để resume single được lưu ở
`outputs/full-test-v1/frozen-runtime`; không resume chúng bằng source mới.

Adaptive mới: [thiết kế disagreement review](docs/ADAPTIVE_REVISION.md),
cấu hình `configs/detection.review.yaml` và `configs/classification.review.yaml`.
Biến thể này bỏ planner và chỉ phản biện một vòng khi nhãn ban đầu bất đồng;
đã chạy đủ dev10 cho hai task: [kết quả và trace](reports/ADAPTIVE_REVIEW_DEV.md).
Accuracy đạt 80% ở cả hai, giảm 62–66% token so với adaptive gần nhất;
chưa vượt single và chưa chạy lại full-test.

Lần sửa và chạy lại mới nhất: [kết quả v3/v4 và trace](reports/NVIDIA_V3_RESULTS.md).
58 kiểm thử đạt; planner v4 hết lỗi validation trong run detection 10 mẫu.
Detection tăng điểm, classification giảm điểm: chưa coi prompt mới là cải thiện chung.

Code, dữ liệu upstream đã ghim, môi trường `.venv`, kiểm thử và smoke test offline có sẵn trong repo local. API NVIDIA `openai/gpt-oss-20b` đã được kết nối và chạy trên dev; xem [kết quả API thật](reports/NVIDIA_DEV_SMOKE.md). **Chưa chạy benchmark toàn bộ test split.** Các trace có `synthetic: true` chỉ kiểm tra plumbing, không đo năng lực LLM. Xem thêm [báo cáo bàn giao](reports/RESULTS.md), [dataset verification](reports/dataset_verification.json) và [khác biệt với upstream](docs/UPSTREAM_AUDIT.md).

## Chạy nhanh trên Windows

Trong PowerShell:

```powershell
cd C:\Users\yoga\Downloads\cocolofa_pard
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe scripts/verify_dataset.py
.\.venv\Scripts\python.exe scripts/smoke_matrix.py
```

Nếu bắt đầu từ bản clone mới:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
git clone https://github.com/Crowd-AI-Lab/cocolofa.git upstream/cocolofa
git -C upstream/cocolofa checkout c39d45fdd57401e1f6cb674f25113dfa0304e734
git clone https://github.com/zigzag2025/PARD.git upstream/PARD
git -C upstream/PARD checkout b34807ce339b05518c998a51b5741917de01c917
.\.venv\Scripts\python.exe scripts/prepare_data.py
.\.venv\Scripts\python.exe scripts/verify_dataset.py
```

Linux/macOS: dùng `.venv/bin/python` thay cho `.\.venv\Scripts\python.exe`. Chạy các lệnh tại thư mục gốc repo. `requirements.txt` là dependency runtime; `requirements-dev.txt` thêm pytest; lock ghi lại phiên bản đã kiểm thử.

## Chạy API thật trên dev

### NVIDIA NIM đã kiểm tra kết nối

Hai cấu hình `configs/detection.nvidia.yaml` và `configs/classification.nvidia.yaml`
dùng endpoint `https://integrate.api.nvidia.com/v1`, model `openai/gpt-oss-20b`,
temperature 1 và giới hạn output 4096 token. Client hiện tại đã được kiểm tra bằng
request thật với JSON Schema; không cần cài thêm SDK `openai`.

```powershell
$env:NVIDIA_API_KEY = "YOUR_NVIDIA_API_KEY"
.\.venv\Scripts\python.exe -m src.run_detection --config configs/detection.nvidia.yaml --limit 10 --output outputs/nvidia-detection-dev
.\.venv\Scripts\python.exe -m src.run_classification --config configs/classification.nvidia.yaml --limit 10 --output outputs/nvidia-classification-dev
```

Thêm `--mode single` và chọn output khác để chạy baseline single-agent. Thêm
`--resume` vào đúng lệnh cũ để tiếp tục. Key chỉ được truyền qua biến môi trường
của process; repo không lưu key. Giá token để `null` vì chưa đối chiếu hóa đơn;
token usage vẫn được ghi đầy đủ. Kết quả dev subset không phải benchmark test.

Tham khảo [model NVIDIA](https://docs.api.nvidia.com/nim/reference/openai-gpt-oss-20b).

### Các provider API

Lớp LLM dùng chung một contract cho agent, cache, retry, audit và structured
validation. Chọn provider trong `model`:

| Provider | Endpoint mặc định/mẫu | Biến môi trường key | Ghi chú |
|---|---|---|---|
| `openai` | `https://api.openai.com/v1` | `OPENAI_API_KEY` | OpenAI Chat Completions |
| `openai_compatible` | NVIDIA hoặc endpoint tương thích | tùy `api_key_env` | Dùng cho NVIDIA và provider tương thích OpenAI |
| `gemini` | `https://generativelanguage.googleapis.com/v1beta` | `GEMINI_API_KEY` | Gemini native `generateContent` |
| `mock` | không gọi mạng | không cần | Chỉ smoke test, không phải kết quả model |

Ví dụ chạy ARS bằng Gemini:

```powershell
$env:GEMINI_API_KEY = "YOUR_GEMINI_API_KEY"
.\.venv\Scripts\python.exe -m src.run_detection --config configs/detection.gemini.yaml --limit 10 --output outputs/gemini-detection-ars-dev10
.\.venv\Scripts\python.exe -m src.run_classification --config configs/classification.gemini.yaml --limit 10 --output outputs/gemini-classification-ars-dev10
.\.venv\Scripts\python.exe -m src.run_detection --config configs/detection.gemini.ars.yaml --limit 10 --output outputs/gemini-detection-ars-review-dev10
.\.venv\Scripts\python.exe -m src.run_classification --config configs/classification.gemini.ars.yaml --limit 10 --output outputs/gemini-classification-ars-review-dev10
```

Gemini native nhận system instruction riêng và JSON structured output qua
`responseJsonSchema`; adapter lọc các keyword JSON Schema ngoài subset provider,
nhưng validator nội bộ vẫn kiểm tra schema đầy đủ sau khi nhận response. Xem
[Gemini generateContent](https://ai.google.dev/api/generate-content) và
[Gemini structured output](https://ai.google.dev/gemini-api/docs/structured-output?lang=rest).

### Endpoint OpenAI hoặc nhà cung cấp khác

Sửa `model.name: SET_MODEL_SNAPSHOT` trong **cả hai** file `configs/detection.yaml`, `configs/classification.yaml` thành cùng một model/snapshot mà tài khoản của bạn truy cập được. Cấu hình mặc định dùng OpenAI Chat Completions; endpoint tương thích có thể dùng `provider: openai_compatible` và đổi `base_url`, `api_key_env`.

```powershell
$env:OPENAI_API_KEY = "YOUR_API_KEY"
.\.venv\Scripts\python.exe -m src.run_detection --config configs/detection.yaml --mode single --limit 10 --output outputs/dev-detection-single
.\.venv\Scripts\python.exe -m src.run_classification --config configs/classification.yaml --mode single --limit 10 --output outputs/dev-classification-single
.\.venv\Scripts\python.exe -m src.run_detection --config configs/detection.yaml --limit 10 --output outputs/dev-detection-pard
.\.venv\Scripts\python.exe -m src.run_classification --config configs/classification.yaml --limit 10 --output outputs/dev-classification-pard
```

Key chỉ đọc từ biến môi trường; không ghi vào config, cache hay Git. `.env` không tự được load. Một số model không nhận `temperature`; đặt `temperature: null` để bỏ tham số. Tăng `max_completion_tokens` nếu model bị cắt output. `structured_output: false` dùng JSON mode cho endpoint không hỗ trợ JSON Schema, nhưng vẫn validate schema và enum ở client. Không có silent fallback khi provider báo lỗi.

Điền ba mức giá token trong YAML nếu cần ước tính USD; code không hard-code giá dịch vụ. Thiếu giá hoặc usage không đầy đủ thì chi phí là `null`. Tổng chi phí thực tế vẫn đối chiếu hóa đơn provider, vì request timeout có thể đã được xử lý phía server.

## Freeze trước khi chạy test

Sau khi kiểm tra và chỉnh trên **dev**, cố định model/prompt/config; không chỉnh theo test labels:

```powershell
.\.venv\Scripts\python.exe scripts/freeze_experiment.py --config configs/detection.yaml --output reports/frozen-detection-v1.json
.\.venv\Scripts\python.exe scripts/freeze_experiment.py --config configs/classification.yaml --output reports/frozen-classification-v1.json
.\.venv\Scripts\python.exe -m src.run_detection --config configs/detection.yaml --split test --frozen reports/frozen-detection-v1.json --output outputs/test-detection-v1
.\.venv\Scripts\python.exe -m src.run_classification --config configs/classification.yaml --split test --frozen reports/frozen-classification-v1.json --output outputs/test-classification-v1
```

Không dùng `--limit` cho benchmark toàn split. Test detection phải có **798** mẫu; classification **481** mẫu. Freeze bao gồm source Python, prompt, config thực thi, phiên bản runtime và hash cả ba file dữ liệu. Đổi một trong những thành phần này cần freeze mới. File output/freeze hiện có không bị ghi đè ngầm.

## Resume và đánh giá

Chạy lại đúng lệnh cũ với `--resume` để bỏ qua sample đã xong và thử lại sample lỗi. Giữ nguyên config, selection, source và freeze. Cache còn cho phép replay sang output mới mà không gọi API lại.

```powershell
.\.venv\Scripts\python.exe -m src.run_detection --config configs/detection.yaml --limit 10 --output outputs/dev-detection-pard --resume
.\.venv\Scripts\python.exe -m src.evaluate --predictions outputs/dev-detection-pard/predictions.jsonl --output outputs/dev-detection-pard/rescored.json
```

Đánh giá không cần key hoặc gọi mạng. Nó yêu cầu `manifest.json` bên cạnh predictions và kiểm tra fingerprint, đủ ID, gold, task, nhãn và status. Sample lỗi không bị bỏ qua để tăng điểm. Run lỗi dừng ở mẫu đầu tiên, ghi `status: incomplete`, `metrics: null`, trả exit code khác 0. Nếu chỉ dòng audit cuối bị ghi dở, resume giữ byte lỗi trong file quarantine rồi tiếp tục; corruption ở giữa log bị từ chối.

Detection báo positive-class Precision/Recall/F1; classification báo Macro-F1 trên đủ tám nhãn, kể cả nhãn không xuất hiện trong subset; zero division = 0. Confusion matrix có hàng là gold, cột là prediction, theo thứ tự `labels` trong summary.

## Ablation và context

| Cấu hình | Luồng |
|---|---|
| `--mode single` | Một API call |
| `--mode no_deliberation` | Ba analysis → arbiter |
| `--mode fixed --protocol round_robin` | Trao đổi tuần tự |
| `--mode fixed --protocol point_counterpoint` | Hai nhóm 1v2 hoặc 2v1 |
| `--mode fixed --protocol cross_examination` | Một examiner, hai respondents |
| `--mode adaptive` | Ba analysis → planner → protocol được chọn → arbiter |
| `adaptive_policy: ars_no_debate` | Decomposer → Acceptability / Relevance / Sufficiency → arbiter |
| `adaptive_policy: ars_review` | ARS diagnoses → synchronous role-preserving review → arbiter |

ARS V1 được mô tả trong [ARS Diagnostic V1](docs/ARS_DIAGNOSTIC_V1.md). Hai policy
giữ nguyên các baseline legacy và Diagnostic V1; chuyên gia ARS chỉ đánh giá
Acceptability / Relevance / Sufficiency, còn `ARSArbiter` là thành phần duy nhất
được nhìn ontology nhãn CoCoLoFa. Dùng `cache/ars-v1` cho run ARS mới và tạo
cache directory khác (`cache/ars-v1-run1`, ...) khi cần run độc lập ở temperature 1.

`engine.max_rounds` nhận 1–5, mặc định 3; không bắt buộc debate một vòng. `engine.early_stop: false` chạy hết budget. Với fixed mode, thứ tự mặc định Factual → Logical → Contextual; examiner là Factual. Adaptive mode có planner chọn vai trò và budget, cấm point-counterpoint khi không có đúng hai nhóm prediction tự nhiên.

`context: paper` dùng **title + immediate parent + target**, theo prompt Appendix C. Không thêm nội dung article mặc định. `article` thêm text từ HTML sẵn có; `comment_only` bỏ title và parent. Hai setting này là ablation riêng, không được đánh dấu là ứng viên so sánh trực tiếp với bảng gốc.

Không có truncation ngầm; context quá dài làm API run lỗi có log. Parent chỉ tìm trong cùng article, trước filtering classification. Mẫu `399:10493` tham chiếu `5338` ở article khác trong train: giữ sample và để parent rỗng, không kéo train vào test.

## Kết quả và trace

Mỗi thư mục run có:

- `manifest.json`: config/source/data fingerprint, sample selection và gold dành cho evaluator.
- `samples/<hashed-id>.json`: checkpoint atomic, prediction, initial/final reports, plan, deliberation, arbiter, status, usage, model versions.
- `predictions.jsonl`: export theo thứ tự nguyên bản của split.
- `raw_calls.jsonl`: request không có key, raw response, lỗi, retry, token usage, timestamp, latency và cache hit.
- `summary.json`: metric, coverage/synthetic flag, model versions, usage và chi phí ước tính.

Gold chỉ được thêm ở runner/evaluator; engine nhận `ModelInput` chỉ chứa text. Không đưa manifest hoặc annotation metadata vào prompt. Một output directory chỉ nên có **một process ghi**. Cache SQLite lưu response đã validate, gồm raw response để replay có thể audit lại. Cache key gồm dataset hash, split, task, sample, role, stage, protocol, toàn bộ model config, prompt/schema và fingerprint experiment.

Trong Cross-Examination, examiner đặt câu hỏi và reflection; prediction trong `final_agents` của examiner vẫn là initial prediction. Dùng transcript để phân tích đóng góp examiner, không coi giá trị này là một lần bỏ phiếu lại. Explanation là tóm tắt ngắn dựa trên text, không phải truy xuất suy nghĩ nội bộ của model.

## Mã nguồn

`src/data/` xử lý schema/context/split; `src/llm/` cung cấp transport/cache/retry; `src/prompts.py` định nghĩa role và task; `src/schemas.py` validate; `src/protocols/` chứa ba protocol; `src/engine.py` điều phối; `src/runner.py` chạy/freeze/resume; `src/evaluate.py` metric. `scripts/` có chuẩn bị dữ liệu, verify, freeze và smoke matrix.

## Nguồn và giới hạn so sánh

[CoCoLoFa paper](https://aclanthology.org/2024.emnlp-main.39/), [CoCoLoFa repo](https://github.com/Crowd-AI-Lab/cocolofa), [PARD paper](https://aclanthology.org/2026.findings-acl.1227/), [PARD repo](https://github.com/zigzag2025/PARD). API format đối chiếu [OpenAI Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs) và [Chat Completions](https://developers.openai.com/api/reference/resources/chat/subresources/completions/methods/create).

`direct_comparison_candidate` chỉ xác nhận các điều kiện kỹ thuật được code kiểm tra; không khẳng định tái tạo bảng paper. Upstream CoCoLoFa không kèm baseline/evaluation code ở commit đã kiểm tra; exact metric implementation và một số chi tiết context không thể xác minh từ code. Prompt/model mới và các adaptation PARD được ghi rõ trong [UPSTREAM_AUDIT.md](docs/UPSTREAM_AUDIT.md). API sampling có thể không deterministic dù temperature=0; dùng snapshot + cache + trace để audit.
