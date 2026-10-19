import json
from pathlib import Path

v4_path = Path("outputs/marketplace-classification-adversarial-gptoss120b-dev66-v1/predictions.jsonl")
rows = [json.loads(line) for line in v4_path.read_text(encoding="utf-8").strip().split("\n")]

full_traces = []
table_rows = []

for idx, row in enumerate(rows, 1):
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
out_json = Path("reports/traces_adversarial_marketplace_gptoss120b_full.json")
out_json.parent.mkdir(parents=True, exist_ok=True)
out_json.write_text(json.dumps(full_traces, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"Exported full traces to {out_json} ({len(full_traces)} samples)")

# Write Markdown report
md_lines = [
    "# BÁO CÁO KẾT QUẢ ĐỐI KHÁNG 3-AGENT: GPT-OSS-120B (MARKETPLACE)",
    "",
    "## 1. TỔNG QUAN HIỆU NĂNG: GPT-OSS-120B VS LLAMA-3.2-11B",
    "",
    "| Chỉ số | GPT-OSS-120B (Marketplace) | Llama-3.2-11B V4 (NVIDIA) | Llama-3.2-11B V3 (Baseline) |",
    "| :--- | :---: | :---: | :---: |",
    f"| **Độ chính xác (Accuracy)** | **25/66 (37.88%)** | **28/66 (42.42%)** | 24/66 (36.36%) |",
    "| **Macro-F1** | **35.96%** | **38.11%** | 31.24% |",
    "| **Ca lật có hại (Harmful Flips)** | **0 ca (0.0%)** | **0 ca (0.0%)** | 12 ca (Phá hủy kết quả) |",
    "| **Tỷ lệ bảo vệ mẫu đúng** | **24/24 (100.0%)** | **26/26 (100.0%)** | 14/26 (53.8%) |",
    "",
    "---",
    "",
    "## 2. BẢNG CHI TIẾT 66 MẪU (FULL AUDIT TABLE)",
    "",
    "| STT | Sample ID | Gold | Prosecutor Candidate | Defender Alternative | Final V4 | Phân loại Lật nhãn |",
    "| :---: | :---: | :--- | :--- | :--- | :--- | :--- |"
]

for row in table_rows:
    md_lines.append(f"| {row['idx']} | `{row['sample_id']}` | **{row['gold']}** | {row['cand']} | {row['alt']} | **{row['final']}** | {row['category']} |")

out_md = Path("reports/marketplace_gptoss120b_sample_level_flip_analysis.md")
out_md.write_text("\n".join(md_lines), encoding="utf-8")
print(f"Exported Markdown report to {out_md}")
