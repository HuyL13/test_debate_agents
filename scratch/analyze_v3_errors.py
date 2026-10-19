import json
from pathlib import Path

dev_data = {s["sample_id"]: s for s in json.loads(Path("data/dev_classification_errors/dev.json").read_text(encoding="utf-8"))}

v3_dir = Path("outputs/nvidia-classification-adversarial-llama11b-dev66-v3/samples")
traces = [json.loads(p.read_text(encoding="utf-8")) for p in v3_dir.glob("*.json")]

errors = []
for t in traces:
    gold = t["gold"]
    pred = t.get("prediction")
    if pred != gold:
        sid = t["sample_id"]
        pros = t.get("prosecutor", {})
        df = t.get("defender", {})
        arb = t.get("arbiter", {})
        dev_sample = dev_data.get(sid, {})

        p_cand = pros.get("candidate_class")
        p_ru = pros.get("runner_up_class")
        d_alt = df.get("alternative_class")
        d_concede = df.get("concede_charge")

        # Determine error type
        if p_cand == gold:
            err_type = "TYPE_B_PROSECUTOR_RIGHT_OVERRULED"
        elif p_ru == gold:
            err_type = "TYPE_C_RUNNERUP_WAS_GOLD"
        elif d_alt == gold:
            err_type = "TYPE_D_DEFENDER_WAS_GOLD"
        else:
            err_type = "TYPE_A_ALL_AGENTS_MISSED"

        errors.append({
            "sample_id": sid,
            "gold": gold,
            "prediction": pred,
            "err_type": err_type,
            "comment": dev_sample.get("comment", ""),
            "pros_cand": p_cand,
            "pros_ru": p_ru,
            "pros_quote": pros.get("quote", ""),
            "pros_defect": pros.get("defect_mechanism", ""),
            "def_concede": d_concede,
            "def_alt": d_alt,
            "def_quote": df.get("counter_quote", ""),
            "def_interp": df.get("charitable_interpretation", ""),
            "arb_pred": pred,
            "arb_content": arb.get("content", arb.get("reasoning", "")),
        })

print(f"Total wrong cases: {len(errors)}")
type_counts = {}
for e in errors:
    type_counts[e["err_type"]] = type_counts.get(e["err_type"], 0) + 1
print("Error types count:", type_counts)

# Group errors by Gold class
by_gold = {}
for e in errors:
    by_gold.setdefault(e["gold"], []).append(e)

for gold, items in sorted(by_gold.items()):
    print(f"\n=== GOLD: {gold} ({len(items)} ca sai) ===")
    for item in items:
        print(f"[{item['sample_id']}] Pred: {item['prediction']} | Type: {item['err_type']}")
        print(f"  Pros: Cand={item['pros_cand']}, RU={item['pros_ru']}")
        print(f"  Def: Concede={item['def_concede']}, Alt={item['def_alt']}")
        print(f"  Comment: {item['comment'][:100]}...")
