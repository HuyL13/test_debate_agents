# NVIDIA API — dev smoke runs

**Adaptive redesigned after stopping full-test:** [disagreement-review results and traces](ADAPTIVE_REVIEW_DEV.md).
Both dev10 tasks reached 80% accuracy; token counts fell 62–66% versus the immediately
preceding adaptive runs. The new method still does not beat the single reference.
Adaptive full-test remains stopped; only the existing single runs continue.

**Full test follow-up:** [live paper comparison](FULL_TEST_COMPARISON.md).
This separate frozen evaluation runs all 798 detection and 481 classification
test comments for each of single and adaptive. Pending cells are not dev scores.

**Latest code revision and rerun:** [v3/v4 results and full traces](NVIDIA_V3_RESULTS.md).
Detection single accuracy increased from 0.80 to 0.90; adaptive from 0.60 to 0.70.
The constrained v4 planner completed 104 calls without validation failures.
Classification regressed by 0.10 accuracy for both modes; the prompt revision is
not an across-task quality improvement. The tables below retain the original runs.

**Full historical trace:** [7 runs / 277 API attempts](traces/README.md), including
the interrupted pre-fix runs, every failed retry, per-agent outputs and links to
the exact original request/response log lines. In the old classification run,
`237:10009` had three correct initial predictions but failed at the planner;
in v2 its initial predictions were already wrong. Execution recovery and
classification quality must be assessed separately.

Model: `openai/gpt-oss-20b`; endpoint: `https://integrate.api.nvidia.com/v1`.
Temperature 1, output budget 4096, JSON Schema enabled, title + immediate parent context.
Credential supplied by the user and passed only in process environment.

These are the first 10 eligible samples in original dev order for each task, with
no random resplit. Classification uses gold positives independently. They are
small smoke subsets, not test benchmark results or evidence of model superiority.

Reviewed 2026-09-07. All four runs are complete; predictions were rescored from
disk with manifest validation. Within each task the two methods used identical
sample IDs. Machine-readable evidence: [nvidia_api_results.json](nvidia_api_results.json).

| Task | Method | Samples | Accuracy | Main metric | API calls | Total tokens |
|---|---|---:|---:|---:|---:|---:|
| Detection | Single | 10 | 0.80 | F1 = 0.666667 | 10 | 6,807 |
| Detection | Adaptive v2 | 10 | 0.60 | F1 = 0.500000 | 115 | 175,516 |
| Classification | Single | 10 | 0.90 | Macro-F1 = 0.611111 | 11 | 8,882 |
| Classification | Adaptive v2 | 10 | 0.80 | Macro-F1 = 0.569444 | 104 | 154,487 |

Detection precision falls from 0.50 to 0.333333; recall remains 1.0, based on only
two positive examples. False positives increase from 2 to 4. Across both tasks,
adaptive consumes approximately 21 times the single-agent token count in these runs.
This measures recorded token use, not monetary charges.

## Giới hạn của subset

Detection chỉ gồm một article, với 8 negative và 2 positive. Classification chỉ
gồm hai article và năm nhãn: False Dilemma (5), Slippery Slope (2), Appeal to Nature
(1), Appeal to Authority (1), Appeal to Majority (1). Macro-F1 vẫn chia cho đủ 8
nhãn theo protocol; ngay cả dự đoán đúng 10/10 cũng chỉ đạt 5/8 = 0.625 trên subset
này. Không sửa metric để làm điểm cao hơn. Chưa đủ bằng chứng kết luận adaptive
kém nói chung hoặc quy nguyên nhân hoàn toàn cho kiến trúc; temperature=1 và chỉ
một lượt mỗi cấu hình cũng tạo bất định.

## Những gì trace cho thấy

1. **Detection bị tăng false positive trong deliberation.** Ở `237:5508` và
   `237:10008`, Factual ban đầu dự đoán Fallacious, còn Logical và Contextual dự
   đoán Non-Fallacious, khớp gold. Sau trao đổi, cả ba trở thành Fallacious và
   arbiter theo kết luận đó. Lý do lặp lại là không có bằng chứng cho nhận định
   hoặc đề xuất; đó chưa tự nó chứng minh một logical fallacy. Đây là quan sát
   trực tiếp ở hai trace, chưa phải chứng minh Factual gây hại trên toàn dataset.
2. **Một số premise bị diễn giải mạnh hơn text.** Ở `237:5207`, câu nói US hợp
   pháp hóa hôn nhân đồng giới *10 năm trước* bị giải thích thành US *mất 10 năm*
   để hợp pháp hóa; câu suy đoán về social media bị biến thành khẳng định nhân quả.
   Cả single và adaptive đều sai so với gold ở mẫu này. Deliberation lặp lại
   premise sai thay vì kiểm tra lại target text.
3. **Classification có lỗi ngay từ initial reports.** `237:10009` có gold Slippery
   Slope và single dự đoán đúng; cả ba initial agents chọn Hasty Generalization,
   rồi CE/arbiter giữ nguyên. Ở `226:4874`, cả single và adaptive chọn Hasty
   Generalization thay vì gold False Dilemma. Không sửa gold khi model bất đồng.
4. **Deliberation cũng có ích ở một mẫu.** `226:5476` có ba initial predictions
   khác nhau; Round-Robin kết thúc ở Appeal to Majority, đúng gold. Không nên bỏ
   toàn bộ deliberation chỉ từ điểm trung bình của 10 mẫu.
5. **Protocol hợp schema chưa chắc đúng chức năng.** Ở CE của `237:10009`, trường
   question chứa nguyên target comment thay vì một câu hỏi phản biện. Reflection
   sau đó tuyên bố vấn đề đã giải quyết. JSON validation không bắt được lỗi ngữ nghĩa này.
6. **Planner vẫn tốn retry.** Detection v2 có 7 response planner không hợp lệ
   (order thiếu vai trò hoặc PC thiếu phân nhóm), nhưng đã retry thành công; không
   có sample thất bại. Classification v2 có 104 call và không có response lỗi.

## Hướng xử lý đề xuất, chưa áp dụng vào engine

**Ưu tiên 1 — sửa độ ổn định của planner.** Giới hạn phần model phải quyết định
ở protocol, topic, examiner và budget. Với PC, code xây dựng/kiểm tra nhóm trực
tiếp từ initial predictions; với RR dùng thứ tự hợp lệ. Đây là cách thực thi
hard constraints bằng code, không dùng gold. Hoặc giữ planner đầy đủ nhưng dùng
schema theo từng protocol và gửi chính lỗi validation vào prompt retry. Không
âm thầm đổi protocol sau lỗi; ghi rõ mọi sửa/repair trong trace.

**Ưu tiên 2 — sửa tiêu chuẩn đánh giá và sự trung thành với input.** Factual phải
phân biệt thiếu kiểm chứng với suy luận sai; không coi mọi unsupported assertion
là fallacy. Yêu cầu giải thích ngắn chỉ ra đoạn text, premise, conclusion và bước
suy luận sai cụ thể; giữ nguyên các dấu hiệu bất định như maybe/can/I think và
phân biệt mốc thời gian với thời lượng. Arbiter kiểm tra lại các luận điểm trong
target, không coi việc nhiều agent lặp lại cùng một diễn giải là bằng chứng mới.
Giữ nguyên ba role; không thêm kiến trúc mới hoặc retrieval.

**Ưu tiên 3 — phân biệt các nhãn dễ nhầm và kiểm tra CE.** Đối chiếu Slippery Slope
(chuỗi hệ quả leo thang không được bảo đảm) với Hasty Generalization (suy rộng từ
trường hợp/mẫu không đủ). CE phải hỏi một vấn đề cụ thể về reasoning hoặc label
đối thủ; không chép target vào question. Lấy ví dụ few-shot từ train nếu cần,
không nhúng chính các mẫu dev đang đánh giá hay dùng test để chỉnh prompt.

**Ưu tiên 4 — ablation và mở rộng đánh giá trên dev.** So sánh single,
three-roles/no-deliberation, fixed RR/PC/CE và adaptive với cùng model, input,
temperature và tập mẫu. Có thể dùng subset dev chẩn đoán nhiều article/đủ tám
nhãn, ghi rõ là subset; kết quả chính nên chạy toàn dev gốc. Chạy lặp các cấu hình
được chọn với cache độc lập cho mỗi lượt để đo biến động (đổi output thôi sẽ replay
cache, không tạo lần lấy mẫu mới). Chỉ đánh giá temperature thấp hơn như một
ablation riêng, không thay khác nhau giữa hai phương pháp. Freeze trước test.

Không tăng số vòng hay đổi sang model khác làm bước đầu: hiện có dấu hiệu lặp lại
lỗi chung, trong khi lượng token đã tăng mạnh. Sau khi sửa prompt/validator, giữ
cùng model để xác định phần cải thiện đến từ thay đổi nào.

The classification single run needed one retry after a response with no JSON
content. Original adaptive runs exposed overvalidation of unused planner fields:
classification stopped at sample 2, and detection was interrupted to apply the fix.
Their traces are retained in `outputs/nvidia-*-adaptive-dev10`; final post-fix runs
use the separate `-v2` directories. Only complete runs may supply scores.

Price estimates remain unknown (`null`); provider token counts are recorded.
The user states this API access is free. No price claim is inferred from token usage.

Configuration: `configs/detection.nvidia.yaml`, `configs/classification.nvidia.yaml`.
Source change: unused teams validated only for point-counterpoint; 55 tests passed.
