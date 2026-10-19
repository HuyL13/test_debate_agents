import json
import sys
from pathlib import Path

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.data.loader import load_split, select_task

data_path = Path("data/dev_classification_errors/dev.json")
raw_samples = select_task(load_split(data_path), "classification")
sample_map = {s.sample_id: s for s in raw_samples}

samples_dir = Path("outputs/nvidia-classification-adversarial-llama11b-dev66/samples")
traces = [json.loads(p.read_text(encoding="utf-8")) for p in samples_dir.glob("*.json")]

# Group 1: 12 ca Gold HG/SS -> Prosecutor WP
hg_ss_to_wp = []
for t in traces:
    if t["gold"] in ("Hasty Generalization", "Slippery Slope") and t["prosecutor"]["candidate_class"] == "Appeal to Worse Problems":
        sid = t["sample_id"]
        s_obj = sample_map.get(sid)
        hg_ss_to_wp.append({
            "sample_id": sid,
            "gold": t["gold"],
            "comment": s_obj.comment if s_obj else "",
            "parent_comment": s_obj.parent_comment if s_obj else "",
            "title": s_obj.title if s_obj else "",
            "pros_candidate": t["prosecutor"]["candidate_class"],
            "pros_quote": t["prosecutor"].get("quote", ""),
            "pros_defect": t["prosecutor"].get("defect_mechanism", ""),
            "pros_ru_class": t["prosecutor"].get("runner_up_class", ""),
            "pros_ru_quote": t["prosecutor"].get("runner_up_quote", ""),
            "arb_pred": t.get("prediction", "")
        })

# Group 2: 11 ca Gold SS bi Prosecutor doan sai
ss_wrong = []
for t in traces:
    if t["gold"] == "Slippery Slope" and t["prosecutor"]["candidate_class"] != "Slippery Slope":
        sid = t["sample_id"]
        s_obj = sample_map.get(sid)
        ss_wrong.append({
            "sample_id": sid,
            "gold": t["gold"],
            "comment": s_obj.comment if s_obj else "",
            "parent_comment": s_obj.parent_comment if s_obj else "",
            "title": s_obj.title if s_obj else "",
            "pros_candidate": t["prosecutor"]["candidate_class"],
            "pros_quote": t["prosecutor"].get("quote", ""),
            "pros_defect": t["prosecutor"].get("defect_mechanism", ""),
            "pros_ru_class": t["prosecutor"].get("runner_up_class", ""),
            "pros_ru_quote": t["prosecutor"].get("runner_up_quote", ""),
            "arb_pred": t.get("prediction", "")
        })

output_data = {
    "hg_ss_to_wp": hg_ss_to_wp,
    "ss_wrong": ss_wrong
}

Path("scratch/error_cases_extracted.json").write_text(json.dumps(output_data, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"Extracted {len(hg_ss_to_wp)} cases of HG/SS -> WP.")
print(f"Extracted {len(ss_wrong)} cases of SS wrong.")
