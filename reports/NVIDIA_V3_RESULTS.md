# NVIDIA: dev rerun after code improvements

Kết luận: detection tăng 10 điểm phần trăm accuracy ở cả single và adaptive;
classification giảm 10 điểm ở cả hai. Schema planner v4 hoàn tất 104 lượt gọi
không có lỗi validation. Giữ tách biệt cải thiện độ ổn định với chất lượng nhãn:
chưa nên coi prompt mới là baseline tốt hơn cho classification. Cần đánh giá trên
dev rộng hơn, đủ tám nhãn và nhiều lần chạy trước khi chọn cấu hình cuối.

Validation: **58 tests passed**. All four reported complete runs were rescored
from predictions with manifest validation and identical sample IDs checked.

Same first 10 eligible dev samples, model, temperature and budgets as the prior runs. Prompts were revised using these dev traces: this is development feedback, not held-out evidence.

Changes: validation-error feedback on retries; text fidelity and inference criteria in shared prompts; explicit competing-interpretation questions in cross-examination.

| Task | Mode | Accuracy old → latest | F1 old → latest | Tokens old → latest |
|---|---|---|---|---|
| detection | single | 0.800 → 0.900 | 0.667 → 0.800 | 6,807 → 9,428 |
| detection | adaptive | 0.600 → 0.700 | 0.500 → 0.571 | 175,516 → 175,946 |
| classification | single | 0.900 → 0.800 | 0.611 → 0.486 | 8,882 → 10,839 |
| classification | adaptive | 0.800 → 0.700 | 0.569 → 0.444 | 154,487 → 208,870 |

F1 means positive-class F1 for detection and macro-F1 over all eight labels for classification. Only five classification labels occur here; the maximum macro-F1 on this subset is 0.625.

Attempt counts include three sandbox network failures per v3 run (zero returned tokens). The runs resumed after network approval. Tokens include provider retries. No test data was evaluated.

Adaptive detection v3 stopped at `237:5509` after three invalid planner attempts; one resume also failed. It is excluded from the complete-run metric table. Detection v4 uses a schema enumerating valid role orders and fixing teams from initial prediction groups; point-counterpoint is excluded when no two-group split exists. This structural revision does not change the Single prompt; classification v3 retains the earlier planner schema and is identified separately.

[Failed v3 run and resume: all 73 audit events](traces/nvidia-detection-adaptive-dev10-v3.md).
That failed experiment consumed 111,447 recorded tokens. Total recorded tokens for
this entire iteration, including the failed run, are **516,530**; the complete-run
table alone totals 405,083. These are token counts, not billing amounts.

## detection / single

[Complete trace](traces/nvidia-detection-single-dev10-v3.md)

Recorded attempts: 13; invalid attempts: 3. The first three attempts were blocked locally by the sandbox before any provider response.

- `237:5207`: Fallacious → Non-Fallacious

## detection / adaptive

[Complete trace](traces/nvidia-detection-adaptive-dev10-v4.md)

Recorded attempts: 104; invalid attempts: 0. Fresh v4 run with constrained planner schema.

- `237:10008`: Fallacious → Non-Fallacious

## classification / single

[Complete trace](traces/nvidia-classification-single-dev10-v3.md)

Recorded attempts: 13; invalid attempts: 3. The first three attempts were blocked locally by the sandbox before any provider response.

- `226:5476`: Appeal to Majority → Hasty Generalization

## classification / adaptive

[Complete trace](traces/nvidia-classification-adaptive-dev10-v3.md)

Recorded attempts: 115; invalid attempts: 4. The first three attempts were blocked locally by the sandbox before any provider response.

- `226:5476`: Appeal to Majority → Hasty Generalization
