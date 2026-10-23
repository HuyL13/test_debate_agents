import json

with open('outputs/marketplace-classification-adversarial-llama70b-test481-v1/summary.json', encoding='utf-8') as f:
    v1 = json.load(f)
with open('outputs/marketplace-classification-adversarial-llama70b-test481-phase1/summary.json', encoding='utf-8') as f:
    p1 = json.load(f)

print(f"Overall Accuracy: v1 = {v1['accuracy']*100:.2f}% -> phase1 = {p1['accuracy']*100:.2f}% (+{(p1['accuracy']-v1['accuracy'])*100:+.2f}%)")
print(f"Overall Macro-F1: v1 = {v1['macro_f1']*100:.2f}% -> phase1 = {p1['macro_f1']*100:.2f}% (+{(p1['macro_f1']-v1['macro_f1'])*100:+.2f}%)")
print("\nPer-class comparison (F1):")
for cls in v1['labels']:
    f1_v1 = v1['per_class'][cls]['f1'] * 100
    f1_p1 = p1['per_class'][cls]['f1'] * 100
    diff = f1_p1 - f1_v1
    rec_v1 = v1['per_class'][cls]['recall'] * 100
    rec_p1 = p1['per_class'][cls]['recall'] * 100
    prec_v1 = v1['per_class'][cls]['precision'] * 100
    prec_p1 = p1['per_class'][cls]['precision'] * 100
    print(f"- {cls:24s}: F1 {f1_v1:.2f}% -> {f1_p1:.2f}% ({diff:+.2f}%) | Rec {rec_v1:.1f}% -> {rec_p1:.1f}% | Prec {prec_v1:.1f}% -> {prec_p1:.1f}%")
