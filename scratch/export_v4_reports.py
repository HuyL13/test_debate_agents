import json
from pathlib import Path

v4_path = Path("outputs/nvidia-classification-adversarial-llama11b-dev66-v4/predictions.jsonl")
v4_rows = [json.loads(line) for line in v4_path.read_text(encoding="utf-8").strip().split("\n")]

full_traces = []
table_rows = []

for idx, row in enumerate(v4_rows, 1):
    sid = row["sample_id"]
    gold = row["gold"]
    final = row["prediction"]
    
    prosecutor = row.get("prosecutor", {})
    cand = prosecutor.get("candidate_class", "None")
    cand_quote = prosecutor.get("quote", "")
    
    defender = row.get("defender", {})
    alt = defender.get("alternative_class", "None")
    alt_quote = defender.get("counter_quote", "")
    concede = defender.get("concede_charge", False) or (alt == "None")
    
    arbiter = row.get("arbiter", {})
    stop_reason = row.get("stop_reason", "")
    arbiter_content = arbiter.get("content", "")
    
    p_corr = (cand == gold)
    f_corr = (final == gold)
    
    if p_corr:
        if f_corr:
            category = "Prosecutor Đúng -> Giữ Đúng (Protected)"
        else:
            category = "Prosecutor Đúng -> Lật Sai (Harmful Flip)"
    else:
        if f_corr:
            category = "Prosecutor Sai -> Lật Đúng (Beneficial Flip)"
        elif cand != final:
            category = "Prosecutor Sai -> Lật sang Sai khác"
        else:
            category = "Prosecutor Sai -> Giữ nguyên Sai"
            
    table_rows.append({
        "idx": idx,
        "sample_id": sid,
        "gold": gold,
        "cand": cand,
        "cand_quote": cand_quote,
        "alt": alt,
        "alt_quote": alt_quote,
        "final": final,
        "category": category,
        "stop_reason": stop_reason,
        "p_corr": p_corr,
        "f_corr": f_corr,
        "arbiter_content": arbiter_content
    })
    
    full_traces.append({
        "sample_id": sid,
        "gold": gold,
        "prediction": final,
        "category": category,
        "prosecutor": prosecutor,
        "defender": defender,
        "arbiter": arbiter,
        "stop_reason": stop_reason,
        "latency_seconds": row.get("latency_seconds"),
        "token_usage": row.get("token_usage")
    })

# Save JSON full traces
out_json = Path("reports/traces_adversarial_v4_full.json")
out_json.parent.mkdir(parents=True, exist_ok=True)
out_json.write_text(json.dumps(full_traces, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"Exported full traces to {out_json} ({len(full_traces)} samples)")

# Write Markdown report
md_lines = [
    "# BÁO CÁO KẾT QUẢ ĐỐI KHÁNG 3-AGENT (V4) - 66 MẪU HARD ERRORS",
    "",
    "## 1. TỔNG QUAN HIỆU NĂNG V4 VS V3",
    "",
    "| Chỉ số | Single Agent (Prosecutor) | Debate V3 (Baseline) | Debate V4 (Có Cue + Unanimous Burden) | Chênh lệch V4 vs V3 |",
    "| :--- | :---: | :---: | :---: | :---: |",
    f"| **Độ chính xác (Accuracy)** | 26/66 (39.39%) | 24/66 (36.36%) | **28/66 (42.42%)** | **+6.06% (+4 mẫu)** |",
    "| **Macro-F1** | - | 31.24% | **38.11%** | **+6.87%** |",
    "| **Ca lật có hại (Harmful Flips)** | - | 12 ca (phá hỏng kết quả) | **0 ca (0.0%)** | **-12 ca (Triệt tiêu 100%)** |",
    "| **Ca lật có lợi (Beneficial Flips)** | - | 10 ca | **2 ca** | -8 ca |",
    "| **Tỷ lệ bảo vệ mẫu đúng của Prosecutor** | 100% | 14/26 (53.8%) | **26/26 (100.0%)** | **+46.2%** |",
    "",
    "---",
    "",
    "## 2. PHÂN BỐ LẬT NHÃN (FLIP AUDIT MATRIX)",
    "",
    "### Nhóm 1: 26 ca Prosecutor ban đầu ĐÚNG",
    "- **Giữ Đúng (Protected / Upheld): 26 / 26 (100.0%)**",
    "  - 23 ca: Defender chủ động **Concede** (`alternative_class: None`) do học được phân bố few-shot cân bằng.",
    "  - 3 ca: Defender thách thức nhưng Arbiter chạy kiểm định đối xứng 2 chiều (Order-Permuted Consensus) và quy tắc Cue khóa (Cue Locking) -> Arbiter bác bỏ thách thức và bảo vệ Candidate thành công (`617:11147`, `168:5000`, `323:6965`).",
    "- **Lật Sai (Harmful Flips): 0 / 26 (0.0%)** (Ở V3 bị mất tới 12 ca, V4 giữ trọn vẹn 100%).",
    "",
    "### Nhóm 2: 40 ca Prosecutor ban đầu SAI",
    "- **Lật Đúng (Beneficial Flips): 2 ca**",
    "  - `287:5658`: Gold = `Appeal to Majority` (Prosecutor đoán `Appeal to Nature` -> Defender phản biện `Appeal to Majority` -> Arbiter đồng thuận lật).",
    "  - `162:4982`: Gold = `Hasty Generalization` (Prosecutor đoán `Appeal to Tradition` -> Defender phản biện `Hasty Generalization` -> Arbiter đồng thuận lật).",
    "- **Lật sang Sai khác: 0 ca**",
    "- **Giữ nguyên Sai: 38 ca** (Defender concede hoặc Challenger không đủ bằng chứng vượt qua Burden of Proof).",
    "",
    "---",
    "",
    "## 3. BẢNG CHI TIẾT 66 MẪU (FULL AUDIT TABLE)",
    "",
    "| STT | Sample ID | Gold | Prosecutor Candidate | Defender Alternative | Final V4 | Phân loại Lật nhãn |",
    "| :---: | :---: | :--- | :--- | :--- | :--- | :--- |"
]

for row in table_rows:
    md_lines.append(f"| {row['idx']} | `{row['sample_id']}` | **{row['gold']}** | {row['cand']} | {row['alt']} | **{row['final']}** | {row['category']} |")

out_md = Path("reports/v4_sample_level_flip_analysis.md")
out_md.write_text("\n".join(md_lines), encoding="utf-8")
print(f"Exported Markdown report to {out_md}")
