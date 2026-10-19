import json
from pathlib import Path

v1 = json.loads(Path("outputs/nvidia-classification-adversarial-llama11b-dev66/summary.json").read_text(encoding="utf-8"))
v2 = json.loads(Path("outputs/nvidia-classification-adversarial-llama11b-dev66-v2/summary.json").read_text(encoding="utf-8"))
v3 = json.loads(Path("outputs/nvidia-classification-adversarial-llama11b-dev66-v3/summary.json").read_text(encoding="utf-8"))

labels = v3["labels"]

print(f"{'Class':26s} | {'V1 Precision':18s} | {'V2 Precision':18s} | {'V3 Precision':18s} | {'Support (Gold)':14s}")
print("-" * 105)

for idx, c in enumerate(labels):
    cm1 = v1["confusion_matrix"]
    tp1 = cm1[idx][idx]
    pred1 = sum(cm1[r][idx] for r in range(len(labels)))
    p1 = v1["per_class"][c]["precision"] * 100

    cm2 = v2["confusion_matrix"]
    tp2 = cm2[idx][idx]
    pred2 = sum(cm2[r][idx] for r in range(len(labels)))
    p2 = v2["per_class"][c]["precision"] * 100

    cm3 = v3["confusion_matrix"]
    tp3 = cm3[idx][idx]
    pred3 = sum(cm3[r][idx] for r in range(len(labels)))
    p3 = v3["per_class"][c]["precision"] * 100

    sup = v3["per_class"][c]["support"]

    str1 = f"{p1:5.1f}% ({tp1:2d}/{pred1:2d})"
    str2 = f"{p2:5.1f}% ({tp2:2d}/{pred2:2d})"
    str3 = f"{p3:5.1f}% ({tp3:2d}/{pred3:2d})"

    print(f"{c:26s} | {str1:18s} | {str2:18s} | {str3:18s} | {sup:2d}")
