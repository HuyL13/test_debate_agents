import json
from pathlib import Path

v3_dir = Path("outputs/nvidia-classification-adversarial-llama11b-dev66-v3/samples")
traces = [json.loads(p.read_text(encoding="utf-8")) for p in v3_dir.glob("*.json")]

dev_data = {s["sample_id"]: s for s in json.loads(Path("data/dev_classification_errors/dev.json").read_text(encoding="utf-8"))}

by_gold = {}
for t in traces:
    if t["gold"] != t.get("prediction"):
        by_gold.setdefault(t["gold"], []).append(t)

out_path = Path("scratch/error_report.md")
with out_path.open("w", encoding="utf-8") as out:
    for g in sorted(by_gold.keys()):
        items = by_gold[g]
        out.write(f"\n## Gold Class: {g} ({len(items)} ca sai)\n\n")
        for i, t in enumerate(items, 1):
            sid = t["sample_id"]
            pred = t.get("prediction")
            p = t.get("prosecutor", {})
            d = t.get("defender", {})
            a = t.get("arbiter", {})
            c = dev_data[sid]["comment"]
            
            p_cand = p.get("candidate_class")
            p_ru = p.get("runner_up_class")
            p_q = p.get("quote")
            d_concede = d.get("concede_charge")
            d_alt = d.get("alternative_class")
            d_q = d.get("counter_quote")
            arb_res = a.get("content", a.get("reasoning", ""))
            
            # Diagnosis
            if p_cand == g:
                diag = "Prosecutor ĐÚNG ở Candidate -> Defender lật sang Runner-up -> Arbiter phán theo Defender"
            elif p_ru == g:
                diag = "Prosecutor đoán nhầm Candidate, nhưng ĐÚNG ở Runner-up -> Defender/Arbiter không chọn Runner-up"
            elif d_alt == g:
                diag = "Defender đoán ĐÚNG ở Alternative -> Nhưng Arbiter phán sai"
            else:
                diag = "Cả 3 Agent đều không nhận diện được nhãn Gold"
                
            out.write(f"### ({i}) Ca `{sid}`: Gold = **{g}** $\\to$ Dự đoán = **{pred}**\n")
            out.write(f"- **Cơ chế lỗi**: {diag}\n")
            out.write(f"- **Target Comment**: *\"{c}\"*\n")
            out.write(f"- **Bước 1 (Prosecutor)**:\n")
            out.write(f"  - Candidate: `{p_cand}` (Quote: *\"{p_q}\"*)\n")
            out.write(f"  - Runner-up: `{p_ru}`\n")
            out.write(f"  - Lý giải: {p.get('defect_mechanism')}\n")
            out.write(f"- **Bước 2 (Defender)**:\n")
            out.write(f"  - Concede: `{d_concede}`\n")
            out.write(f"  - Alternative: `{d_alt}` (Quote: *\"{d_q}\"*)\n")
            out.write(f"  - Lập luận: {d.get('charitable_interpretation')}\n")
            out.write(f"- **Bước 3 (Arbiter)**:\n")
            out.write(f"  - Phán quyết: `{pred}`\n")
            out.write(f"  - Lý do: {arb_res}\n\n")
