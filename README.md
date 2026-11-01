# CoCoLoFa — Dialectical Debate

Repo chỉ giữ **flow dialectical đầu tiên**: Prosecutor → Defender → DialecticalArbiter. Các vai trò là những lần gọi cùng model cấu hình, không phải ba model được huấn luyện riêng. Baseline single-call chỉ phục vụ đối chứng.

## Chạy nhanh

Yêu cầu Python 3.11+. Từ thư mục repo, trong PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe scripts/smoke_test.py
```

Smoke dùng mock và dữ liệu tự tạo, **không gọi API và không đo năng lực model**. Linux/macOS dùng `.venv/bin/python`.

### Dữ liệu CoCoLoFa

Repo kèm đủ `data/cocolofa/train.json`, `dev.json`, `test.json`, khớp hash phiên bản upstream đã ghim. Có thể kiểm tra trực tiếp bằng `python scripts/verify_dataset.py`. Các lệnh dưới chỉ cần khi muốn lấy lại dữ liệu từ nguồn:

```powershell
git clone https://github.com/Crowd-AI-Lab/cocolofa.git upstream/cocolofa
git -C upstream/cocolofa checkout c39d45fdd57401e1f6cb674f25113dfa0304e734
.\.venv\Scripts\python.exe scripts/prepare_data.py
.\.venv\Scripts\python.exe scripts/verify_dataset.py
```

`prepare_data.py` đọc blob Git gốc để tránh thay đổi newline trên Windows. `data/cocolofa/provenance.json` ghi nguồn và hash. Xem [nguồn dữ liệu và refactor](docs/PROVENANCE.md).

### Chạy NVIDIA

Đặt key trong environment; chọn model mà key có quyền truy cập. Các config để `SET_MODEL_SNAPSHOT` nhằm yêu cầu người chạy chọn model rõ ràng. Không có key thật trong config.

```powershell
$env:NVIDIA_API_KEY = "YOUR_NVIDIA_API_KEY"
$env:COCOLOFA_MODEL = "YOUR_ACCESSIBLE_NVIDIA_MODEL_ID"
.\.venv\Scripts\python.exe -m src.run_classification --config configs/classification.nvidia.yaml --model $env:COCOLOFA_MODEL --limit 10
```

Config mẫu dùng temperature 0, timeout 300 giây. Không có marketplace fallback. Client có thể dùng endpoint tương thích khác nếu người chạy chủ động cấu hình.

| Config | Flow |
|---|---|
| `classification.nvidia.yaml` | Flow dialectical gốc |
| `detection.nvidia.yaml` | Detection nhị phân |
| `classification.single.nvidia.yaml` | Baseline classification một call |
| `detection.single.nvidia.yaml` | Baseline detection một call |

### Resume và đánh giá

```powershell
.\.venv\Scripts\python.exe -m src.run_classification --config configs/classification.nvidia.yaml --model $env:COCOLOFA_MODEL --limit 10 --resume
.\.venv\Scripts\python.exe -m src.evaluate --predictions outputs/classification-dev/predictions.jsonl
```

Resume phải dùng đúng config, model, dữ liệu, source và lựa chọn mẫu của lượt cũ. Không resume output lịch sử bằng source sau refactor. File đã hoàn tất được tái sử dụng; lỗi API/contract được lưu rõ, không coi là kết quả thành công. `--limit` là smoke/prefix subset, không đại diện một benchmark cân bằng.

Trước khi chạy TEST, đặt model thực và `split: test` trong bản config thí nghiệm, rồi freeze:

```powershell
.\.venv\Scripts\python.exe scripts/freeze_experiment.py --config configs/my-test.yaml --output outputs/my-test.freeze.json
.\.venv\Scripts\python.exe -m src.run_classification --config configs/my-test.yaml --frozen outputs/my-test.freeze.json
```

Freeze ghi config/source/data fingerprint; evaluator kiểm tra đủ mẫu và đúng manifest trước khi báo điểm. `confidence` không được hiệu chuẩn; cost theo đơn giá cấu hình, không phải hóa đơn provider. Trace có thể chứa nguyên văn dữ liệu đầu vào, nên không tự động publish raw run.

## Cấu trúc repo

```text
configs/                  # Detection/classification + single-call controls
src/
  engine.py               # Điều phối dialectical hoặc single
  runner.py               # Chạy, freeze, resume và ghi trace
  run_classification.py
  run_detection.py
  evaluate.py
  schemas.py              # JSON validation/quote normalization dùng chung
  labels.py
  io_utils.py
  dialectical/
    debate.py
    prompts.py
    schemas.py
    validation.py
    fallacy_definitions.py
  baseline/single.py      # Prompt single-call đối chứng
  data/                   # Loader và xác minh dữ liệu
  llm/                    # Client, transport, mock, cache, usage
scripts/                  # Prepare/verify/freeze và smoke offline
tests/                    # Test agent, grounding, runner, client, baseline
docs/                     # Chi tiết policy, provenance và bản I/O độc lập
```

`outputs/`, `cache/`, `reports/`, `scratch/`, dataset và `.env` là artifact local được Git bỏ qua. README chứa đầy đủ bài toán và I/O bên dưới; [bản riêng](docs/DIALECTICAL_TASK_AND_AGENT_IO.vi.md) dùng để chia sẻ.

---

Repo chỉ giữ **flow dialectical đầu tiên**: Prosecutor → Defender → DialecticalArbiter. Các vai trò là những lần gọi cùng model cấu hình, không phải ba model được huấn luyện riêng. Baseline single-call chỉ phục vụ đối chứng.

## 1. Bài toán tổng

Nhận một bình luận dưới bài báo, dùng ngữ cảnh để nhận diện lỗi lập luận và trả nhãn kèm giải thích. Mục tiêu là kiểm tra phản biện có giúp phân loại tốt hơn một LLM gọi trực tiếp hay không, với chi phí bao nhiêu.

| Task | Tập mẫu | Output |
|---|---|---|
| Detection | Tất cả bình luận | `Fallacious` / `Non-Fallacious` |
| Classification | Chỉ gold-positive | Một trong tám nhãn fallacy |

Classification không cascade từ kết quả detection. Gold dùng để chọn tập/chấm điểm, không đưa vào agent. Đây là đánh giá cách lập luận, không xác minh tính đúng sai của bài báo bằng nguồn bên ngoài.

8 nhãn: Appeal to Authority, Appeal to Majority, Appeal to Nature, Appeal to Tradition, Appeal to Worse Problems, False Dilemma, Hasty Generalization, Slippery Slope.

### Ví dụ tổng

Các ví dụ là **minh họa tự tạo, không phải trace benchmark**. Confidence do model tự báo, chưa được hiệu chuẩn.

Input **X**, mặc định title + comment cha trực tiếp + TARGET:

```json
{
  "title": "Debate about book restrictions",
  "parent_comment": "What policy should the council adopt?",
  "comment": "We must either ban these books or our whole society will eventually collapse. There is no middle ground."
}
```

Output classification hiển thị cho người dùng:

```json
{
  "prediction": "False Dilemma",
  "confidence": 0.84,
  "content": "The comment forces a choice between banning books and societal collapse, excluding other options."
}
```

Cùng input, detection trả `Fallacious`. Không có comment cha thì dùng chuỗi rỗng. Toàn bài báo chỉ được cấp khi chọn `context: article`; mặc định `paper` không cấp toàn bài.

## 2. Flow classification gốc

```mermaid
flowchart TD
    X["Bình luận + ngữ cảnh"] --> P["Prosecutor: đề xuất 2 nhãn + quote"]
    P --> D["Defender: xem xét nhãn chính"]
    X --> D
    D --> C["Code kiểm tra quote và cue, chuẩn hóa phản biện"]
    C --> Q{"Defender đồng ý sau kiểm tra?"}
    Q -- "Có" --> A["Arbiter xác nhận; code giữ nhãn chính"]
    Q -- "Không" --> B["Arbiter so sánh 2 lần, đảo thứ tự phương án"]
    B --> U{"Cả hai lần chọn nhãn thay thế?"}
    U -- "Có" --> ALT["Chọn nhãn thay thế"]
    U -- "Không" --> MAIN["Giữ nhãn chính"]
```

Luật gốc **ưu tiên giữ nhãn chính**. Runner-up của Prosecutor giúp Defender cân nhắc, nhưng không tự động được đưa vào mọi lượt Arbiter; nhánh tranh chấp dùng primary và alternative thực tế của Defender.

### 2.1. Chuẩn bị dữ liệu — code

- **Input:** bản ghi dataset, title, quan hệ comment cha, annotation.
- **Output:** `ModelInput` có dạng X; giữ gold và metadata ngoài input LLM.
- Code: `src/data/loader.py`.

### 2.2. Prosecutor — agent đề xuất

- **Input:** X + định nghĩa tám nhãn + prompt vai trò; chưa thấy phản biện.
- **Output P:** hai nhãn khác nhau, cơ chế lỗi và quote nguyên văn từ TARGET.

```json
{
  "has_fallacy_charge": true,
  "candidate_class": "False Dilemma",
  "defect_mechanism": "The comment treats banning the books or societal collapse as exhaustive options.",
  "quote": "We must either ban these books or our whole society will eventually collapse.",
  "runner_up_class": "Slippery Slope",
  "runner_up_defect": "The comment also predicts an unsupported severe consequence.",
  "runner_up_quote": "our whole society will eventually collapse."
}
```

### 2.3. Defender — agent phản biện

- **Input:** X + P tại `reports.prosecutor_indictment`.
- **Nhiệm vụ:** đồng ý với primary hoặc đưa một nhãn thay thế có căn cứ. Không được dùng nhãn không-fallacy cho task classification.
- **Output D**, ví dụ đồng ý:

```json
{
  "concede_charge": true,
  "alternative_class": "None",
  "charitable_interpretation": "The explicit denial of a middle ground supports False Dilemma more directly than a consequence-chain reading.",
  "counter_quote": "There is no middle ground."
}
```

Nếu phản đối, `concede_charge` là false và `alternative_class` phải là một nhãn khác. Quote và cơ chế thay thế phải vượt kiểm tra code trước khi chuyển sang tranh chấp.

### 2.4. Validator — code, không phải agent

- **Input:** X, P, D.
- **Kiểm tra:** schema JSON, nhãn, trích dẫn; các rule cue/grounding/locking của bản gốc.
- **Output:** D sau kiểm tra/chuẩn hóa. Ví dụ D ở trên vẫn là đồng ý.
- Code có thể chuyển phản biện thành đồng ý khi alternative/quote không đạt các điều kiện của flow gốc. Vì vậy phải phân biệt response model và kết quả sau rule; rule không bảo đảm ngữ nghĩa đúng.
- Code: `src/dialectical/schemas.py`, `src/dialectical/validation.py`.

### 2.5. DialecticalArbiter — agent trọng tài

**Nhánh đồng ý:** nhận X và phần reports sau:

```json
{
  "comment": "We must either ban these books or our whole society will eventually collapse. There is no middle ground.",
  "candidate": {
    "class": "False Dilemma",
    "quote": "We must either ban these books or our whole society will eventually collapse."
  }
}
```

Sample output:

```json
{
  "prediction": "False Dilemma",
  "confidence": 0.84,
  "content": "The statement explicitly excludes a middle ground."
}
```

Sau call xác nhận, code gốc giữ `candidate_class` ngay cả khi Arbiter trả nhãn khác.

**Nhánh tranh chấp:** nhận X và hai phương án dưới dạng `option_1`, `option_2`, mỗi phương án có `class`, `quote`. Gọi hai lần với thứ tự đảo nhau. Mỗi call chỉ được chọn một trong hai nhãn, output có `prediction`, `confidence`, `content`.

Ví dụ bộ tổng hợp nhận:

```json
{
  "primary": "False Dilemma",
  "alternative": "Slippery Slope",
  "run_a": "Slippery Slope",
  "run_b": "False Dilemma",
  "final_prediction": "False Dilemma"
}
```

Đây là **minh họa input/output của luật tổng hợp**, không phải schema response của một agent. Vì hai lượt không cùng chọn alternative nên giữ primary. Hai thứ tự cùng dùng một model, không phải đồng thuận giữa hai model độc lập.

### 2.6. Điều phối, lưu trace và đánh giá — code

| Module | Input | Output |
|---|---|---|
| Engine | X + task + model config | Trace có prediction, Prosecutor, Defender, Arbiter, stop_reason, thời gian |
| Client | System prompt + user payload + schema | Response JSON, usage, cache và audit; retry lỗi theo cấu hình |
| Bộ tổng hợp | Hai prediction của Arbiter khi tranh chấp | Chỉ đổi sang alternative nếu cả hai lượt chọn alternative |
| Scorer | Prediction + gold ngoài model | Accuracy, macro-F1, confusion matrix và thống kê từng nhãn |

Mỗi call LLM có payload chung gồm `input`, `reports`, `history`, `instruction`, `question`, `plan`; history rỗng và plan null trong flow này. Không có agent planner. Các trường trace lịch sử `planner_protocol`/`plan` được giữ để tương thích định dạng lưu kết quả.

## 3. Detection và số call

Detection dùng cùng ba vai trò nhưng không bắt buộc chọn một nhãn fallacy:

- Prosecutor không tìm được lỗi: `has_fallacy_charge: false`, `candidate_class: "None"`, không có các trường runner-up. Code tạo Defender placeholder, rồi gọi Arbiter → **2 call**.
- Có buộc tội: Prosecutor → Defender → Arbiter → **3 call**. Defender không có `alternative_class`; Arbiter trả `Fallacious`/`Non-Fallacious`.
- Classification: nhánh đồng ý **3 call**, tranh chấp **4 call**, chưa tính retry.
- Baseline single: **1 call** cho mỗi task. Đây là đối chứng, không phải policy debate thứ hai.

## 4. Paper chính

1. [CoCoLoFa — Yeh, Wan & Huang, EMNLP 2024](https://aclanthology.org/2024.emnlp-main.39/): dataset và thiết lập hai task đang dùng.
2. [Logical Fallacy Detection — Jin et al., Findings EMNLP 2022](https://aclanthology.org/2022.findings-emnlp.532/): nền tảng LOGIC/LOGICCLIMATE và cấu trúc lập luận.
3. [Boosting Logical Fallacy Reasoning in LLMs via Logical Structure Tree — Lei & Huang, EMNLP 2024](https://aclanthology.org/2024.emnlp-main.730/): hướng khai thác cấu trúc logic; repo này không triển khai LST.
4. [Improving Factuality and Reasoning in Language Models through Multiagent Debate — Du et al., ICML 2024](https://arxiv.org/abs/2305.14325): nền tảng nhiều instance LLM trao đổi và phản biện.
5. [Encouraging Divergent Thinking in Large Language Models through Multi-Agent Debate — Liang et al.](https://arxiv.org/abs/2305.19118): tranh luận đối lập và judge.
6. [PARD: Deconstruct, Diagnose, and Deliberate, Findings ACL 2026](https://aclanthology.org/2026.findings-acl.1227/): nguồn cảm hứng ban đầu; flow này không phải reproduction đầy đủ của PARD.

## 5. Code và giới hạn

- Điều phối: `src/engine.py`; thuật toán gốc: `src/dialectical/debate.py`.
- Prompt: `src/dialectical/prompts.py`; contract: `src/dialectical/schemas.py`.
- Quote/cue rules: `src/dialectical/validation.py`; định nghĩa: `src/dialectical/fallacy_definitions.py`.
- Single baseline: `src/baseline/single.py`.

Giới hạn: primary được ưu tiên theo luật gốc; cue/quote rules có thể chặn một cách diễn giải hợp lý; lời giải thích của model không bảo đảm đúng; nhiều call tốn chi phí và chịu lỗi dịch vụ. Ví dụ/smoke không phải benchmark. Gold-positive classification buộc chọn nhãn dù một số mẫu có thể mơ hồ. Không có web retrieval, huấn luyện, RL, graph hay GEPA trong flow chạy.
