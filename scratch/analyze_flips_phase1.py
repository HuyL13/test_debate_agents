import json

def load_preds(path):
    preds = {}
    with open(path, encoding='utf-8') as f:
        for line in f:
            d = json.loads(line)
            preds[d['sample_id']] = d
    return preds

v1 = load_preds('outputs/marketplace-classification-adversarial-llama70b-test481-v1/predictions.jsonl')
p1 = load_preds('outputs/marketplace-classification-adversarial-llama70b-test481-phase1/predictions.jsonl')

fixed = []
broken = []

for sid, d_v1 in v1.items():
    if sid not in p1:
        continue
    d_p1 = p1[sid]
    gold = d_v1['gold']
    corr_v1 = (d_v1['prediction'].lower() == gold.lower())
    corr_p1 = (d_p1['prediction'].lower() == gold.lower())
    if not corr_v1 and corr_p1:
        fixed.append((sid, gold, d_v1['prediction'], d_p1['prediction']))
    elif corr_v1 and not corr_p1:
        broken.append((sid, gold, d_v1['prediction'], d_p1['prediction']))

print(f"Total Fixed (Wrong in v1 -> Correct in Phase 1): {len(fixed)}")
for sid, gold, pred_v1, pred_p1 in fixed:
    print(f"  [+] Sample {sid}: Gold '{gold}' | v1 predicted '{pred_v1}' -> Phase 1 fixed to '{pred_p1}'")

print(f"\nTotal Regressed (Correct in v1 -> Wrong in Phase 1): {len(broken)}")
for sid, gold, pred_v1, pred_p1 in broken:
    print(f"  [-] Sample {sid}: Gold '{gold}' | v1 predicted '{pred_v1}' -> Phase 1 predicted '{pred_p1}'")
