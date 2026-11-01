# Dữ liệu, phương pháp và khả năng tái lập

- Dataset: [CoCoLoFa](https://github.com/Crowd-AI-Lab/cocolofa), commit `c39d45fdd57401e1f6cb674f25113dfa0304e734`. Repo kèm ba split nguyên gốc với hash được kiểm tra; giữ attribution và điều khoản của upstream.
- Paper dataset: [Yeh et al., EMNLP 2024](https://aclanthology.org/2024.emnlp-main.39/).
- PARD là nguồn cảm hứng của các thử nghiệm ban đầu, không phải thuật toán được tái hiện đầy đủ ở đây. Repo hiện chỉ giữ dialectical debate và baseline single.

## Cleanup cho GitHub

Code được gom vào `src/dialectical/`; chỉ giữ flow dialectical gốc và baseline single-call đối chứng. Các flow ARS, planner, diagnostic, graph và những biến thể debate làm sau đó được lưu ngoài repo. Prompt và luật quyết định của flow đầu tiên được giữ; system prompt của baseline được đối chiếu giữ nguyên. Mock chỉ phục vụ kiểm tra offline.

Dataset, cache, output/raw trace, báo cáo thử nghiệm và tài liệu viết bài cũ được giữ local hoặc trong backup, không đưa vào cây file publish. Không rewrite lịch sử Git. Kết quả cũ vẫn gắn với source/fingerprint cũ; không dùng source sau cleanup để resume thí nghiệm đó.

README không công bố các điểm smoke hoặc kết quả từ tập đã dùng chẩn đoán như một benchmark mới. Để báo điểm mới, freeze config và source trước TEST, lưu đủ trace và đánh giá trên tập đủ coverage.

## Input không chứa nhãn

`ModelInput` chỉ cấp title, target và comment cha; toàn bài báo là tùy chọn. Gold dùng để chọn tập classification và chấm điểm, không được truyền vào agent. Mỗi mẫu classification đã được dataset xác nhận thuộc một trong tám lớp, nhưng nhãn đúng cụ thể không được cấp cho LLM.
