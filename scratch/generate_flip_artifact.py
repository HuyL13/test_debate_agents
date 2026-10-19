import json
from pathlib import Path

# Paths
v3_dir = Path("outputs/nvidia-classification-adversarial-llama11b-dev66-v3/samples")
dev_data_path = Path("data/dev_classification_errors/dev.json")
artifact_dir = Path(r"C:\Users\Admin\.gemini\antigravity-ide\brain\7f23332d-9a7d-4450-a681-8ce61aaceb0f")
workspace_report_path = Path("reports/sample_level_flip_analysis_v3.md")
artifact_report_path = artifact_dir / "sample_level_flip_analysis_v3.md"

dev_data = {s["sample_id"]: s for s in json.loads(dev_data_path.read_text(encoding="utf-8"))}

traces = [json.loads(p.read_text(encoding="utf-8")) for p in v3_dir.glob("*.json")]
# Sort traces consistently by sample_id
traces.sort(key=lambda t: t["sample_id"])

pros_correct = []
pros_wrong = []
all_samples = []

for t in traces:
    sid = t["sample_id"]
    gold = t["gold"]
    final = t.get("prediction")
    
    pros = t.get("prosecutor", {})
    df = t.get("defender", {})
    arb = t.get("arbiter", {})
    
    p_cand = pros.get("candidate_class", "None")
    p_ru = pros.get("runner_up_class", "None")
    p_q = pros.get("quote", "")
    p_ru_q = pros.get("runner_up_quote", "")
    
    d_concede = df.get("concede_charge", False)
    d_alt = df.get("alternative_class", "None")
    d_q = df.get("counter_quote", "")
    
    arb_reason = arb.get("content", arb.get("reasoning", ""))
    
    record = {
        "sid": sid,
        "gold": gold,
        "final": final,
        "p_cand": p_cand,
        "p_ru": p_ru,
        "p_q": p_q,
        "p_ru_q": p_ru_q,
        "d_concede": d_concede,
        "d_alt": d_alt,
        "d_q": d_q,
        "arb_reason": arb_reason,
        "comment": dev_data.get(sid, {}).get("comment", "")
    }
    
    if p_cand == gold:
        if final == gold:
            record["flip_status"] = "Giữ Đúng"
            record["category"] = "pros_correct_kept"
        else:
            record["flip_status"] = "Lật Sai"
            record["category"] = "pros_correct_flipped"
        pros_correct.append(record)
    else:
        if final == gold:
            record["flip_status"] = "Lật Đúng"
            record["category"] = "pros_wrong_flipped_correct"
        elif final != p_cand:
            record["flip_status"] = "Lật Sang Sai Khác"
            record["category"] = "pros_wrong_flipped_wrong"
        else:
            record["flip_status"] = "Không Đổi (Vẫn Sai)"
            record["category"] = "pros_wrong_kept_wrong"
        pros_wrong.append(record)
        
    all_samples.append(record)

# Generate Markdown Content
lines = []
lines.append("# Báo Cáo Phân Tích Lật Nhãn Từng Mẫu (Adversarial Debate V3 - Dev66)")
lines.append("")
lines.append("> **Mô hình**: `meta/llama-3.2-11b-vision-instruct`  ")
lines.append("> **Bộ dữ liệu**: `data/dev_classification_errors/dev.json` (66 mẫu chẩn đoán khó)  ")
lines.append("> **Thư mục đầu ra**: [`outputs/nvidia-classification-adversarial-llama11b-dev66-v3`](file:///d:/PaperResearch/multi-agent/test_debate_agents/outputs/nvidia-classification-adversarial-llama11b-dev66-v3/summary.json)  ")
lines.append("")
lines.append("---")
lines.append("")
lines.append("## 1. Bảng Tổng Hợp Động Lực Lật Nhãn (Flip Dynamics)")
lines.append("")
lines.append("| Nhóm khởi đầu | Hành vi của Arbiter | Số lượng | Tỷ lệ trong nhóm | Tác động tới Accuracy chung cuộc |")
lines.append("| :--- | :--- | :---: | :---: | :--- |")
lines.append(f"| **Prosecutor ĐÚNG (26 ca)** | **Giữ đúng** (Arbiter giữ Candidate) | **{len([x for x in pros_correct if x['category'] == 'pros_correct_kept'])}** ca | 53.8% | Bảo toàn điểm đúng |")
lines.append(f"| | **Lật sai** (Arbiter lật sang nhãn sai) | **{len([x for x in pros_correct if x['category'] == 'pros_correct_flipped'])}** ca | 46.2% | **Mất 12 điểm đáng tiếc** *(Chủ yếu là Authority & Worse Problems)* |")
lines.append(f"| **Prosecutor SAI (40 ca)** | **Lật đúng** (Arbiter sửa sai thành đúng) | **{len([x for x in pros_wrong if x['category'] == 'pros_wrong_flipped_correct'])}** ca | 25.0% | **Cứu thêm 10 điểm** *(Chủ yếu đôn Slippery Slope lên)* |")
lines.append(f"| | **Lật sang sai khác** (Đổi sang lớp sai khác) | **{len([x for x in pros_wrong if x['category'] == 'pros_wrong_flipped_wrong'])}** ca | 37.5% | Vẫn sai |")
lines.append(f"| | **Không đổi** (Giữ Candidate sai) | **{len([x for x in pros_wrong if x['category'] == 'pros_wrong_kept_wrong'])}** ca | 37.5% | Vẫn sai |")
lines.append(f"| **TỔNG CỘNG (66 ca)** | **Chung cuộc đúng (14 giữ + 10 cứu)** | **24 ca** | **36.36%** | **Macro-F1 đạt 0.3124** |")
lines.append("")
lines.append("> [!IMPORTANT]")
lines.append("> **Đánh giá hiệu ứng ròng của Arbiter**:  ")
lines.append("> - Arbiter đã lật nhãn ở **37 ca (56.1%)**, và giữ Candidate ở **29 ca (43.9%)**.")
lines.append("> - Trong 37 ca lật: Arbiter cứu đúng được **10 ca** (từ SS runner-up), nhưng lại làm hỏng **12 ca** Prosecutor đã đoán đúng từ đầu (5 Authority, 3 Worse Problems, 2 Tradition, 1 Majority, 1 Nature).")
lines.append("> - Nếu Arbiter có cơ chế chặn không lật 12 ca này, kết quả hệ thống sẽ đạt **36/66 (54.55%)**.")
lines.append("")
lines.append("---")
lines.append("")
lines.append("## 2. Bảng 26 Ca Prosecutor ĐÚNG Ban Đầu (Giữ Đúng vs. Lật Sai)")
lines.append("")
lines.append("| STT | Sample ID | Gold Class | Prosecutor Candidate & Quote | Prosecutor Runner-Up & Quote | Defender Alt & Concede | Final (Arbiter) | Trạng thái | Ghi chú cơ chế lật |")
lines.append("| :---: | :---: | :--- | :--- | :--- | :--- | :--- | :---: | :--- |")

for idx, r in enumerate(pros_correct, 1):
    pq = r['p_q'].replace('|', '/').replace('\n', ' ')
    if len(pq) > 60: pq = pq[:57] + '...'
    ruq = r['p_ru_q'].replace('|', '/').replace('\n', ' ')
    if len(ruq) > 60: ruq = ruq[:57] + '...'
    dq = r['d_q'].replace('|', '/').replace('\n', ' ')
    if len(dq) > 60: dq = dq[:57] + '...'
    
    concede_str = "Concede" if r['d_concede'] else f"Alt: {r['d_alt']}"
    status_badge = f"**{r['flip_status']}**"
    
    note = ""
    if r['category'] == 'pros_correct_flipped':
        note = f"Arbiter bị thuyết phục bởi {r['d_alt']}"
    else:
        note = "Arbiter phê chuẩn Candidate"
        
    lines.append(f"| {idx} | `{r['sid']}` | **{r['gold']}** | `{r['p_cand']}`<br>*{pq}* | `{r['p_ru']}`<br>*{ruq}* | {concede_str}<br>*{dq}* | **{r['final']}** | {status_badge} | {note} |")

lines.append("")
lines.append("---")
lines.append("")
lines.append("## 3. Bảng 40 Ca Prosecutor SAI Ban Đầu (Lật Đúng / Lật Sai / Không Đổi)")
lines.append("")
lines.append("| STT | Sample ID | Gold Class | Prosecutor Candidate & Quote | Prosecutor Runner-Up & Quote | Defender Alt & Concede | Final (Arbiter) | Trạng thái | Đánh giá diễn biến tranh biện |")
lines.append("| :---: | :---: | :--- | :--- | :--- | :--- | :--- | :---: | :--- |")

for idx, r in enumerate(pros_wrong, 1):
    pq = r['p_q'].replace('|', '/').replace('\n', ' ')
    if len(pq) > 60: pq = pq[:57] + '...'
    ruq = r['p_ru_q'].replace('|', '/').replace('\n', ' ')
    if len(ruq) > 60: ruq = ruq[:57] + '...'
    dq = r['d_q'].replace('|', '/').replace('\n', ' ')
    if len(dq) > 60: dq = dq[:57] + '...'
    
    concede_str = "Concede" if r['d_concede'] else f"Alt: {r['d_alt']}"
    status_badge = f"**{r['flip_status']}**"
    
    note = ""
    if r['category'] == 'pros_wrong_flipped_correct':
        note = f"**Cứu thành công**: Đôn `{r['p_ru']}` lên"
    elif r['category'] == 'pros_wrong_flipped_wrong':
        note = f"Đổi từ `{r['p_cand']}` sang `{r['final']}` (vẫn sai)"
    else:
        note = f"Giữ nguyên `{r['p_cand']}` sai"
        
    lines.append(f"| {idx} | `{r['sid']}` | **{r['gold']}** | `{r['p_cand']}`<br>*{pq}* | `{r['p_ru']}`<br>*{ruq}* | {concede_str}<br>*{dq}* | **{r['final']}** | {status_badge} | {note} |")

lines.append("")
lines.append("---")
lines.append("")
lines.append("## 4. Bảng Tra Cứu Toàn Diện 66 Mẫu (Master Table)")
lines.append("")
lines.append("| # | Sample ID | Gold Class | Prosecutor (Cand / RU) | Quotes (Pros Cand / RU) | Defender (Concede / Alt) | Counter-Quote | Final Verdict | Kết quả |")
lines.append("| :---: | :---: | :--- | :--- | :--- | :--- | :--- | :--- | :---: |")

for idx, r in enumerate(all_samples, 1):
    pq = r['p_q'].replace('|', '/').replace('\n', ' ')
    if len(pq) > 50: pq = pq[:47] + '...'
    ruq = r['p_ru_q'].replace('|', '/').replace('\n', ' ')
    if len(ruq) > 50: ruq = ruq[:47] + '...'
    dq = r['d_q'].replace('|', '/').replace('\n', ' ')
    if len(dq) > 50: dq = dq[:47] + '...'
    
    pros_pair = f"**C:** `{r['p_cand']}`<br>**RU:** `{r['p_ru']}`"
    quotes_pair = f"**Q_C:** *{pq}*<br>**Q_RU:** *{ruq}*"
    def_info = f"**Concede:** `{r['d_concede']}`<br>**Alt:** `{r['d_alt']}`"
    
    is_correct = "✅ ĐÚNG" if r['final'] == r['gold'] else "❌ SAI"
    
    lines.append(f"| {idx} | `{r['sid']}` | **{r['gold']}** | {pros_pair} | {quotes_pair} | {def_info} | *{dq}* | **{r['final']}** | {is_correct} |")

content = "\n".join(lines)

# Write to artifact and workspace
artifact_report_path.write_text(content, encoding="utf-8")
workspace_report_path.write_text(content, encoding="utf-8")
print(f"Artifact written to {artifact_report_path}")
print(f"Workspace report written to {workspace_report_path}")
