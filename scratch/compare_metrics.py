import json
from pathlib import Path

v3_summary = json.loads(Path("outputs/nvidia-classification-adversarial-llama11b-dev66-v3/summary.json").read_text(encoding="utf-8"))
v4_summary = json.loads(Path("outputs/nvidia-classification-adversarial-llama11b-dev66-v4/summary.json").read_text(encoding="utf-8"))
mkp_path = Path("outputs/marketplace-classification-adversarial-gptoss120b-dev66-v1/summary.json")
mkp_summary = json.loads(mkp_path.read_text(encoding="utf-8")) if mkp_path.exists() else None
l70_path = Path("outputs/marketplace-classification-adversarial-llama70b-dev66-v1/summary.json")
l70_summary = json.loads(l70_path.read_text(encoding="utf-8")) if l70_path.exists() else None

classes = v4_summary["labels"]

print(f"{'Class':<26} | {'V3 (11B) F1':<11} | {'V4 (11B) F1':<11} | {'GPT-120B F1':<11} | {'Llama-70B Prec':<14} {'Llama-70B Rec':<13} {'Llama-70B F1':<12}")
print("-" * 105)

for c in classes:
    m3 = v3_summary["per_class"][c]
    m4 = v4_summary["per_class"][c]
    f1_m = mkp_summary["per_class"][c]["f1"] * 100 if mkp_summary else 0
    if l70_summary:
        m70 = l70_summary["per_class"][c]
        print(f"{c:<26} | {m3['f1']*100:9.1f}% | {m4['f1']*100:9.1f}% | {f1_m:9.1f}% | {m70['precision']*100:12.1f}% {m70['recall']*100:12.1f}% {m70['f1']*100:10.1f}%")
    else:
        print(f"{c:<26} | {m3['f1']*100:9.1f}% | {m4['f1']*100:9.1f}% | {f1_m:9.1f}% |")

print("-" * 105)
acc3 = v3_summary["accuracy"] * 100
acc4 = v4_summary["accuracy"] * 100
mf1_3 = v3_summary["macro_f1"] * 100
mf1_4 = v4_summary["macro_f1"] * 100
accm = mkp_summary["accuracy"] * 100 if mkp_summary else 0
mf1_m = mkp_summary["macro_f1"] * 100 if mkp_summary else 0
acc70 = l70_summary["accuracy"] * 100 if l70_summary else 0
mf1_70 = l70_summary["macro_f1"] * 100 if l70_summary else 0

print(f"{'OVERALL ACCURACY':<26} | {acc3:9.2f}% | {acc4:9.2f}% | {accm:9.2f}% | {'-':<14} {'-':<13} {acc70:10.2f}%")
print(f"{'OVERALL MACRO-F1':<26} | {mf1_3:9.2f}% | {mf1_4:9.2f}% | {mf1_m:9.2f}% | {'-':<14} {'-':<13} {mf1_70:10.2f}%")

