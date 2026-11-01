# Defender v2 — kế hoạch kiểm chứng và cải thiện phản biện

> Trạng thái: Đề xuất để duyệt; chưa triển khai, chưa chạy API.
> Thực thi sau khi duyệt: dùng superpowers:executing-plans, làm lần lượt theo các task và kiểm chứng trước khi kết luận.

**Goal:** Giảm phản biện gây hại, giữ khả năng sửa HG/Worse Problems, đánh giá trên cùng báo cáo Prosecutor và giữ nguyên Arbiter.

**Architecture:** Defender tạo hồ sơ đối chiếu có cấu trúc về candidate và alternative. Một adapter kiểm tra hợp đồng/bằng chứng rồi chuyển về bốn trường cũ cho Arbiter. Harness replay tái sử dụng nguyên báo cáo Prosecutor và nguyên context, tách đánh giá đề xuất Defender khỏi kết quả sau Arbiter.

**Tech stack:** Python hiện tại, pytest, JSON Schema, runner/cache/manifest hiện có; không thêm framework, model hay agent mới.

**Spec / căn cứ:** Yêu cầu người dùng trong hội thoại và `reports/DEFENDER_V1_COMPARISON_20261029.md`.

## 1. Bằng chứng và mục tiêu

Trên test đã quan sát, v1 chuyển 187 phản biện tới Arbiter: 28 alternative đúng, 148 đổi candidate đúng thành sai, 11 đổi sai sang sai. Trong 28 cơ hội sửa đúng, HG có 13 và Worse Problems có 8. False Dilemma được đề xuất 41 lần nhưng đúng 3. 154 phản biện chọn runner-up, chỉ 21 đúng; không được mặc định runner-up tốt hơn chỉ vì có cách diễn giải hợp lý.

Prosecutor giữa hai lượt đã khác 24 nhãn. Vì thế không dùng kết quả 420 so với 417 để suy ra tác động nhân quả của Defender. Mọi so sánh tiếp theo phải replay cùng một báo cáo đầu vào, không chỉ cùng tên model hay temperature.

## 2. Global constraints

- Classification là phạm vi duy nhất. Detection giữ nguyên.
- Giữ nguyên prompt, schema, thứ tự gọi và logic lựa chọn Prosecutor.
- Giữ nguyên prompt, payload, schema, hai lượt đảo thứ tự và policy cuối của Arbiter.
- Không thêm LLM call xác minh ở v2 đầu tiên. Không tăng Top-k.
- Không cấm quote trùng, không dùng regex làm bằng chứng đúng/sai về ngữ nghĩa, không khóa theo tên lớp.
- Không đưa gold, trạng thái đúng/sai, quyết định Arbiter hay lời giải thích baseline vào đầu vào model.
- Không sửa manifest cũ, đổi fingerprint để hợp thức hóa resume, hoặc trộn mẫu thuộc hai phiên bản vào cùng run.
- Không sửa thêm parser chung hoặc cơ chế tự đổi enum trong task này. Ghi giới hạn raw_report là báo cáo sau parser; provider text còn ở raw_calls.
- Chỉnh prompt trên train/dev. 481 test đã được xem và dùng để phát hiện lỗi nên lần đánh giá lại chỉ là regression, không phải đánh giá holdout độc lập mới.

## 3. Hướng được đề xuất và các lựa chọn

1. Chỉ siết prompt: ít thay đổi, nhưng không đo được model đã bác candidate hay chỉ biện hộ alternative.
2. Prompt + hồ sơ đối chiếu + gate hợp đồng: đề xuất chọn; thêm quan sát và kiểm tra nguồn evidence, không tuyên bố code hiểu đúng ngữ nghĩa.
3. Gọi một verifier mới cho mỗi phản biện: để sau; tăng chi phí và thêm nhiễu trước khi biết lỗi còn lại.

Không quay lại hard regex: 168 phản biện không có cue chứa cả 24 alternative đúng và 134 phản biện gây hại. Cần phân biệt bằng vai trò suy luận, không chỉ từ khóa.

## 4. Hợp đồng Defender v2

Tạo schema riêng cho v2, không thay schema v1/detection. Đầu ra v2 gồm:

- `decision`: `uphold`, `challenge`, `defer`.
- `premise_quote`, `conclusion_quote`: quote target; cho phép rỗng khi thực sự implicit, khi đó giải thích trong `inference_summary`, không tạo quote giả.
- `inference_summary`: mô tả quan hệ hỗ trợ giữa premise và conclusion, không thêm sự kiện ngoài input.
- `candidate_assessment`: `status` thuộc `supported`, `contradicted`, `not_established`, `secondary_mechanism`, `uncertain`; `condition`, `evidence_quote`, `explanation`.
- `alternative_assessment`: `class`, `status` thuộc `supported`, `not_established`, `uncertain`; `premise_quote`, `conclusion_quote`, `explanation`. Khi không có alternative dùng class `None`, các quote rỗng và status `not_established`.
- `decisive_difference`: một giải thích cụ thể tại sao hai nhãn không giải thích tốt ngang nhau cho bước suy luận chính.
- `counter_quote`, `charitable_interpretation`: giữ ý nghĩa hiện có, luôn có trường, kể cả khi uphold/defer.

JSON mẫu đầy đủ cho cả ba quyết định được ghi trong prompt, không dùng nhãn placeholder ngoài enum. Không yêu cầu quote cho sự vắng mặt: `not_established` phải nêu điều kiện nào chưa được chứng minh; không bịa câu phủ định.

### Quy tắc ra quyết định

- Challenge chỉ khi candidate bị contradicted/not_established, hoặc mô tả cơ chế phụ có chỉ rõ cơ chế chính; alternative supported bằng lập luận có căn cứ; decisive_difference phân biệt trực tiếp hai bên.
- Candidate và alternative đều có căn cứ nhưng chưa phân biệt được vai trò chính: defer.
- Candidate được chứng minh và không có alternative mạnh hơn sau đối chiếu: uphold.
- Chỉ có alternative hợp lý, thiếu quote chứng minh hoặc không nêu lỗi candidate: defer, không tự chế thêm lập luận.
- Không bắt mọi challenge phải có mâu thuẫn trực tiếp với candidate: nhiều lỗi là candidate không đủ điều kiện hoặc chỉ chạm cơ chế phụ.

### Adapter và gate

Tạo `src/defender_review.py` với:

- `validate_defender_review(value, target)` kiểm tra type/enum, trường bắt buộc, các quote không rỗng phải có trong target, tính nhất quán giữa decision và assessment. JSON/quote sai kích hoạt retry hiện có; không âm thầm bù quote hoặc chọn hộ nhãn.
- `normalize_defender_review(prosecutor, review, target)` trả bốn trường cũ cùng audit ngoài payload Arbiter. `uphold` và `defer` đều giữ candidate qua adapter hiện tại; audit phân biệt rõ hai trạng thái. Challenge thiếu hợp đồng phân biệt chuyển `effective_decision=defer`, không ghi model đã đồng thuận. Giữ submitted decision và lý do gate.
- Gate chỉ kiểm tra hợp đồng và nguồn quote. Một model có thể khai `supported` sai; không quảng bá gate này như chứng minh ngữ nghĩa. Chất lượng phải được đo bằng dev và audit thủ công.
- Không đưa hồ sơ mở rộng vào payload Arbiter vì người dùng chưa muốn sửa Agent 3.

## 5. Quy tắc phân biệt cần củng cố

- Majority ↔ HG: phân biệt đồng thuận được dùng làm bằng chứng với suy rộng từ mẫu. Có một sự kiện trong context không tự chứng minh người nói đang lấy nó làm mẫu đại diện.
- Authority ↔ Nature: source có thể hỗ trợ một tiền đề; cần xem bước kết luận đánh giá tốt/xấu có dựa trên naturalness không.
- Worse Problems ↔ FD: ưu tiên/hoãn một giải pháp chưa chứng minh hai lựa chọn loại trừ nhau. Phải kiểm tra cam kết loại trừ.
- HG ↔ SS: giữ khả năng nhận ra mẫu ngầm và analogies có trong input, nhưng phải nối được case → population; dự báo hậu quả không tự là suy rộng.
- Tradition: nhắc lịch sử chưa đủ; phải có tuổi đời được dùng làm lý do chuẩn tắc/đánh giá.
- Không cấm chuyển nhãn nào theo thống kê test. Dùng ví dụ tổng hợp hoặc train để minh họa cả challenge đúng và uphold đúng.

## 6. Review focus

- Replay sai sample/context: hash input + dataset + report, fail fast khi thiếu/trùng/không khớp; không tự gọi lại Prosecutor.
- Quote trùng hợp lệ; quote implicit không bị sửa thành quote giả; quote ngoài target vẫn bị từ chối.
- Đủ cấu trúc nhưng sai ngữ nghĩa: audit dev và metric bắt lỗi; unit test không thể chứng minh prompt tăng accuracy.
- Defer phải giữ prediction hiện có nhưng không được ghi thành đồng thuận trong audit.
- Resume đúng version chạy tiếp, sai source/config/selection phải từ chối; schema wrapper/missing fields có regression test.

## 7. Các task triển khai

### Task 1 — Replay Prosecutor và đo từng ranh giới

**Files:** tạo `scripts/evaluate_defender.py`, `tests/test_defender_evaluation.py`; thêm module `src/defender_experiment.py` nếu cần tách CLI khỏi logic.

**Interfaces:** nhận đường dẫn dataset, tập sample ID cố định, snapshot Prosecutor, variant và thư mục output; xuất raw Defender, effective Defender, optional Arbiter và report metric. Tái sử dụng Client/validator hiện có. Gold chỉ ở evaluator.

- [ ] Viết test replay trả nguyên báo cáo/quote cho sample đúng; thiếu/trùng ID, quote không thuộc target, dataset/context hash khác phải fail trước API.
- [ ] Chạy test và xác nhận đỏ đúng nguyên nhân.
- [ ] Thực hiện replay intercept duy nhất lời gọi `Prosecutor/indictment`; bỏ qua live Prosecutor. Hỗ trợ profile Defender v1 và v2; full pipeline dùng nguyên execute hiện có với profile được chọn.
- [ ] Tách gold khỏi object gửi model; test bằng mẫu gold sentinel không xuất hiện trong request.
- [ ] Snapshot dev được tạo một lần rồi khóa trước so sánh; snapshot test hiện có chỉ phục vụ regression sau cùng.
- [ ] Report correct P, direct-Defender policy (ghi rõ counterfactual), final; precision/recall/F1 theo lớp; đúng→sai, sai→đúng, sai→sai, defer, gate rejection, accepted/rejected correction ở Arbiter; chi phí và retry.
- [ ] Kiểm tra metric bằng fixture có số đếm định trước; lưu rõ denominator, phân biệt raw/normalized/surviving challenges.

### Task 2 — Schema v2, prompt đối chiếu và adapter

**Files:** `src/adversarial_schemas.py`, `src/adversarial_prompts.py`, tạo `src/defender_review.py`, `tests/test_defender_review.py`.

**Interfaces:** schema và validator v2 riêng; adapter trả bốn trường cũ. V1 và detection vẫn gọi schema/prompt hiện tại.

- [ ] Viết các test: shared quote giữ được; wrapper response được parse; thiếu counter_quote retry; quote bịa bị từ chối; same-class không chuyển nhãn; cả hai supported nhưng không phân biệt được thì defer; alternative không có evidence thì defer.
- [ ] Xác nhận test đỏ, rồi thực hiện schema/validator/adapter theo mục 4.
- [ ] Viết prompt bằng checklist mục 5 và JSON đầy đủ; ví dụ từ train/tổng hợp, không lấy nguyên mẫu test đã audit.
- [ ] Test adapter không đổi raw report, ghi submitted/effective decision, giữ rationale; không chuyển trường audit sang Arbiter.
- [ ] Không viết test chỉ grep câu prompt. Kiểm tra request/response contract; hiệu quả prompt dùng thử nghiệm dev.

### Task 3 — Tích hợp profile và lưu trace

**Files:** `src/engine.py`, `src/runner.py`, `src/adversarial_debate.py`, tests tương ứng; configs v2 riêng.

**Interfaces:** `engine.defender_policy` nhận `diagnostic_v1` (default) hoặc `evidence_v2`. Chỉ classification adversarial dùng v2. Config sai tổ hợp phải có lỗi rõ.

- [ ] Test default tái hiện luồng v1; detection giữ nguyên; profile v2 chỉ thay call Defender và normalization.
- [ ] Xác nhận đỏ rồi thêm option, dispatch và audit.
- [ ] Test payload/schema/prompt Prosecutor và Arbiter không đổi giữa profile khi cùng báo cáo/decision đầu vào.
- [ ] Lưu `defender_review`, `defender_effective`, `defender_validation`, phiên bản schema/prompt; giữ các field cũ để evaluator đọc được.
- [ ] Tạo output/manifest/cache identity theo profile; không bỏ kiểm tra fingerprint. Thêm config dev riêng cho Llama, không chạy GPT-OSS trong vòng đầu.

### Task 4 — Đối chứng prompt/gate và audit dev

**Files:** cấu hình experiment, báo cáo dưới `reports/defender-v2/`, tài liệu `docs/DEFENDER_V2.md`.

- [ ] Tạo tập dev cố định khoảng 100 mẫu, chọn theo quy tắc khóa trước, có đủ tám lớp và lỗi Prosecutor; không chỉ chọn hard errors. Lưu selection, không cấp gold cho agent. Report nhỏ chỉ dùng tìm lỗi, không dùng kết luận cuối.
- [ ] B0: Defender v1 + soft validator, cùng snapshot Prosecutor.
- [ ] B1: prompt/schema v2, đánh giá submitted decisions trước decision gate; safety validation vẫn bắt buộc.
- [ ] B2: cùng raw output B1 + decision gate; không gọi LLM lại để đo tác động gate thuần túy.
- [ ] So cùng ngân sách/tokens/temperature; không hạ temperature chỉ cho v2. Nếu thử temperature thì là biến thể riêng.
- [ ] Audit khoảng 20 challenge gây hại, 20 correction đúng (hoặc toàn bộ nếu ít hơn), và 20 defer/blocked challenge. Review input/evidence trước khi xem gold; ghi lỗi missing condition, secondary mechanism, invented sample, wrong scope, vague rationale.
- [ ] Nếu chỉ tăng defer mà không giữ được correction, loại variant, không coi số challenge thấp là thành công.

### Task 5 — Full dev, chọn bản và regression test

- [ ] Sau smoke ổn định, chạy toàn bộ dev cho B0/B1; B2 lấy lại đúng raw B1. Chạy tối thiểu 3 lượt Defender cho baseline và ứng viên cuối nếu ngân sách được chấp thuận khi triển khai; mỗi lượt dùng cùng snapshot Prosecutor.
- [ ] Chọn phiên bản trên dev trước khi xem kết quả test mới. Dùng paired bootstrap hoặc thống kê paired cho chênh lệch cuối; báo khoảng bất định, không chỉ một điểm F1.
- [ ] Freeze source/config/schema/prompt/selection sau lựa chọn; tạo output test mới. Không resume sang phiên bản khác, không chép 8 mẫu cũ vào run mới.
- [ ] Chạy lại 481 test như regression đã quan sát; công bố giới hạn holdout. Nếu cần kết luận khoa học độc lập, cần dữ liệu chưa tham gia chỉnh sửa hoặc giao thức đánh giá khác được xác định trước.

### Task 6 — Verification và bàn giao

- [ ] `python -m pytest` toàn suite; chạy CLI mock với profile mới và fixture replay, kiểm tra resume/frozen mismatch và không rò gold.
- [ ] Đọc diff xác nhận Prosecutor/Arbiter không đổi logic; báo lỗi còn lại, không tuyên bố unit tests chứng minh tăng chất lượng model.
- [ ] Tạo lệnh freeze/run/resume chính xác cho variant được chọn, file kết quả và cách đọc audit. Không tự khởi chạy toàn bộ paid benchmark trong task viết plan.

## 8. Tiêu chí chọn phiên bản (đề xuất, khóa trước full dev)

Điều kiện bắt buộc:

- Đủ coverage; không có gold trong request; không bỏ mẫu lỗi; resume và audit hợp lệ.
- Mức tăng ròng direct Defender `beneficial - harmful` dương trên dev, không chỉ tăng correction recall.
- Final Accuracy và Macro-F1 không thấp hơn B0 trên cùng snapshot trong trung bình các lượt; báo độ bất định thay vì hứa chắc thắng.
- Giữ HG/Worse Problems correction recall tối thiểu 70% của B0 trên cùng dev; nếu mẫu cơ hội quá ít, báo counts và chưa quyết định bằng tỷ lệ này.

Mục tiêu tối ưu, không phải cam kết kết quả:

- Giảm ít nhất 50% harmful challenges so B0, không buộc đạt một challenge rate định sẵn.
- Challenge precision hướng tới >=40%; báo cả sai→sai và sai→đúng riêng.
- Không lớp nào bị mất recall quá 2 điểm % so B0 mà không được phân tích/giải trình; đây là cờ review, không hard-code theo lớp.
- Không thêm LLM call cho mỗi mẫu; báo số call thực tế gồm retry.

## 9. Thứ tự và điểm dừng

Task 1 trước để có đối chứng công bằng; Task 2–3 mới thay hành vi; Task 4 tìm lỗi và đo gate; Task 5 chỉ chạy bản có triển vọng; Task 6 bàn giao. Nếu v2 không vượt v1 trên dev, giữ v1 làm default, lưu v2 dạng thử nghiệm và phân tích lỗi, không tiếp tục nới/siết bằng mẫu test.

Kế hoạch chưa được duyệt. Các ngưỡng ở mục 8 là đề xuất của người lập kế hoạch, không phải yêu cầu đã được người dùng xác nhận.

## Implementation record — 2026-10-29

Implemented the agreed first delivery (tasks 1–3): `src/defender_review.py`, v2 schema, engine policy, replay snapshot/evaluator CLI and dedicated config. Tested contract/gate, unchanged Arbiter payload, exact report replay, bad snapshot rejection, no gold in requests, frozen mismatch, resume and offline mock paths. Full suite: 178 passed before final documentation review. No paid API calls. Tasks 4–5 remain experimental work; no quality gain claimed. See `docs/DEFENDER_V2.md`.

Ruling: keep the v2-specific prompt in `src/defender_review.py` to avoid editing the existing Prosecutor/Arbiter prompt module. Replay uses its own explicit manifest/freeze protocol rather than weakening the existing runner identity checks. Full before/after gate metrics are counterfactual policies; live ungated Arbiter ablation remains future work.
