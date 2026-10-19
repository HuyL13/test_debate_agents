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

wp_samples = [t for t in traces if t["prosecutor"]["candidate_class"] == "Appeal to Worse Problems"]

wp_true = []
wp_false = []

for t in wp_samples:
    sid = t["sample_id"]
    s_obj = sample_map.get(sid)
    item = {
        "sample_id": sid,
        "gold": t["gold"],
        "comment": s_obj.comment if s_obj else "",
        "parent_comment": s_obj.parent_comment if s_obj else "",
        "title": s_obj.title if s_obj else "",
        "pros_quote": t["prosecutor"].get("quote", ""),
        "pros_defect": t["prosecutor"].get("defect_mechanism", ""),
        "pros_ru": t["prosecutor"].get("runner_up_class", ""),
        "pros_ru_quote": t["prosecutor"].get("runner_up_quote", ""),
    }
    if t["gold"] == "Appeal to Worse Problems":
        wp_true.append(item)
    else:
        wp_false.append(item)

output_data = {
    "wp_true": wp_true,
    "wp_false": wp_false
}

Path("scratch/wp_comparison.json").write_text(json.dumps(output_data, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"Exported {len(wp_true)} true WP and {len(wp_false)} false WP.")
