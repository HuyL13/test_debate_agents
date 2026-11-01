# Defender v2: evidence review và paired replay

V2 hiện là profile thử nghiệm, không thay default v1. Chưa có bằng chứng accuracy tăng: toàn bộ kiểm tra ở bước triển khai là offline/mock, không phải benchmark model.

## Cơ chế

- `engine.defender_policy: evidence_v2` chỉ hợp lệ với classification, adaptive, adversarial.
- Defender trả `uphold`, `challenge`, `defer`, premise/conclusion, candidate assessment, alternative assessment và decisive difference.
- Gate yêu cầu objection cụ thể, alternative supported, quote target hợp lệ, và khác biệt quyết định. Gate chỉ kiểm tra hợp đồng và nguồn quote, không chứng minh assessment đúng ngữ nghĩa.
- Quote trùng được phép; regex không phủ quyết. Quote implicit được để rỗng và giải thích trong inference_summary, không tạo quote giả.
- Adapter chuyển về bốn trường cũ cho Arbiter. `concede_charge=true` là cờ tương thích của cả uphold và defer; khi thống kê phải dùng `defender_validation.effective_decision` để phân biệt.
- Không thêm call: Prosecutor, Defender rồi nguyên Arbiter cũ. Prompt/schema/payload/policy của Prosecutor và Arbiter giữ nguyên. Không gửi hồ sơ mở rộng cho Arbiter.

## Artifacts

Mỗi trace v2 có `defender_review`, `defender_effective`, `defender_validation`; report gốc nằm cả ở `defender.raw_report`. Đây là dữ liệu sau parser, không phải raw provider bytes. Provider text và retry ở `raw_calls.jsonl`.

Replay snapshot chỉ chứa sample ID, input/context hash và báo cáo Prosecutor; không chứa gold. Toàn bộ snapshot được kiểm tra dataset hash, context, sample ID, quote và fingerprint trước API. Snapshot thiếu/trùng/mismatch phải fail, không tự gọi lại Prosecutor. Gold chỉ được thêm vào trace đánh giá sau khi engine chạy.

Replay output có `manifest.json`, `prosecutor_replay.jsonl`, `raw_calls.jsonl`, `samples/`, `predictions.jsonl`, `summary.json`. Summary tách Prosecutor, submitted Defender trước gate, effective Defender sau gate và final. Hai cột direct Defender là counterfactual, không phải thí nghiệm hai-agent chạy độc lập. Sample lỗi dừng run, không tính metrics cho phần coverage thiếu.

## 1. Kiểm tra nhanh offline

```bash
python -m pytest -q
python -m src.run_classification \
  --config configs/classification.adversarial.defender-v2.marketplace.yaml \
  --mock --limit 3 --output outputs/defender-v2-mock-dev3
```

Mock chỉ kiểm tra đường ống, luôn ghi synthetic, không dùng đánh giá chất lượng.

## 2. Tạo snapshot dev một lần

Nếu chưa có một lượt v1 dev hoàn tất, chạy v1 một lần (có dùng API):

```bash
python -m src.run_classification \
  --config configs/classification.adversarial.defender-v1.marketplace.yaml \
  --output outputs/defender-v2-source-v1-dev
```

Giữ nguyên mã nguồn trong khi một run chưa hoàn tất; thêm `--resume` đúng cùng lệnh nếu bị ngắt.

Sau khi source run đủ coverage:

```bash
python scripts/evaluate_defender.py snapshot \
  --config configs/classification.adversarial.defender-v2.marketplace.yaml \
  --predictions outputs/defender-v2-source-v1-dev/predictions.jsonl \
  --output reports/prosecutor-fixed-dev-v1.json
```

Snapshot xuất từ predictions yêu cầu manifest đi kèm và mọi mẫu đều `ok`. Lượt dev thiếu coverage không được xuất thành full snapshot. Muốn smoke 100 mẫu, dùng `--limit 100` trên cùng snapshot ở các lượt replay; selection là 100 ID đầu theo snapshot, không phải tập phân tầng đại diện. Không kết luận chất lượng từ subset đó.

## 3. So sánh cùng Prosecutor

```bash
python scripts/evaluate_defender.py run \
  --config configs/classification.adversarial.defender-v1.marketplace.yaml \
  --snapshot reports/prosecutor-fixed-dev-v1.json \
  --limit 100 --output outputs/defender-v1-fixed-dev100

python scripts/evaluate_defender.py run \
  --config configs/classification.adversarial.defender-v2.marketplace.yaml \
  --snapshot reports/prosecutor-fixed-dev-v1.json \
  --limit 100 --output outputs/defender-v2-fixed-dev100
```

Sau đó bỏ `--limit` và chọn thư mục output mới để chạy full dev. Cùng snapshot nghĩa là cùng đầy đủ report/quote/context; model và temperature giữ nguyên. Arbiter vẫn có sampling, nên chênh lệch cuối chưa tách được nhiễu nếu chỉ chạy một lượt. Lặp lại với output khác hiện có thể đọc cache cho cùng identity: để có replicate độc lập phải dùng config với cache_dir khác; không sửa temperature để giả làm replicate. Việc đổi cache_dir không đổi semantic identity nhưng tạo cache độc lập. Tính chi phí tổng trên raw_calls và cache_hits, không cộng replay thành API call.

## 4. Freeze và regression test sau khi chọn trên dev

481 mẫu test đã được phân tích trước nên đây là regression trên tập đã quan sát, không phải holdout mới. Không chỉnh prompt theo điểm test.

Có thể xuất snapshot từ lượt test cũ đã hoàn tất:

```bash
python scripts/evaluate_defender.py snapshot \
  --config configs/classification.adversarial.defender-v2.marketplace.yaml --split test \
  --predictions outputs/defender-v1-formatfix-llama70b-test-20261028/predictions.jsonl \
  --output reports/prosecutor-fixed-test-v1.json

python scripts/evaluate_defender.py freeze \
  --config configs/classification.adversarial.defender-v2.marketplace.yaml --split test \
  --snapshot reports/prosecutor-fixed-test-v1.json \
  --output reports/frozen-defender-v2-replay-test-v1.json

python scripts/evaluate_defender.py run \
  --config configs/classification.adversarial.defender-v2.marketplace.yaml --split test \
  --snapshot reports/prosecutor-fixed-test-v1.json \
  --frozen reports/frozen-defender-v2-replay-test-v1.json \
  --output outputs/defender-v2-fixed-test-v1
```

Nếu ngắt, dùng chính lệnh run cuối và thêm `--resume`. Không thay source/config/snapshot/selection giữa freeze và run/resume. Replay manifest dùng giao thức riêng: không đưa cho `src.run_classification` hoặc `src.evaluate`; xem `summary.json` của evaluate_defender.py. Lượt v1 đối chứng trên test cần freeze riêng tương ứng config v1.

## Giới hạn và phần chưa thực hiện

Đã thực hiện bước 1–3 của plan: replay, contract/gate v2, tích hợp profile và logging. Chưa chạy thử nghiệm dev trả phí, audit ngữ nghĩa, full dev lặp nhiều lần hay lựa chọn phiên bản thắng. Đo pre/post gate hiện có ở direct-policy metrics; chưa có live Arbiter ablation cho submitted decisions không qua gate. Các mục tiêu precision/recall trong plan chưa được xác nhận.
