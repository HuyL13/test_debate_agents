import json
from pathlib import Path

sum_120b = json.loads(Path("outputs/marketplace-classification-adversarial-gptoss120b-dev66-v1/summary.json").read_text(encoding="utf-8"))
sum_11b = json.loads(Path("outputs/nvidia-classification-adversarial-llama11b-dev66-v4/summary.json").read_text(encoding="utf-8"))

classes = sum_120b["labels"]

print(f"{'Fallacy Class':<26} | {'11B-V4 F1':<10} {'11B Rec':<8} | {'120B F1':<10} {'120B Rec':<8} {'120B Prec':<10} | {'Leader':<10}")
print("-" * 85)

for c in classes:
    m11 = sum_11b["per_class"][c]
    m120 = sum_120b["per_class"][c]
    leader = "11B (+)" if m11["f1"] > m120["f1"] else ("120B (+)" if m120["f1"] > m11["f1"] else "Equal")
    print(f"{c:<26} | {m11['f1']*100:6.1f}%    {m11['recall']*100:6.1f}%  | {m120['f1']*100:6.1f}%    {m120['recall']*100:6.1f}%   {m120['precision']*100:6.1f}%   | {leader}")

print("-" * 85)
acc11 = sum_11b["accuracy"] * 100
acc120 = sum_120b["accuracy"] * 100
mf1_11 = sum_11b["macro_f1"] * 100
mf1_120 = sum_120b["macro_f1"] * 100
print(f"{'OVERALL ACCURACY':<26} | {acc11:6.2f}%              | {acc120:6.2f}%                            | {'11B (+4.5%)'}")
print(f"{'OVERALL MACRO-F1':<26} | {mf1_11:6.2f}%              | {mf1_120:6.2f}%                            | {'11B (+2.1%)'}")
