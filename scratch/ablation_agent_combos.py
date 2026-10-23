import json
from sklearn.metrics import classification_report, accuracy_score, f1_score

def evaluate_combos(path):
    y_gold = []
    y_a1 = []      # Agent 1 (Prosecutor only)
    y_a1_a2 = []   # Agent 1 + 2 (Prosecutor + Defender, no Arbiter)
    y_a1_a3 = []   # Agent 1 + 3 (Prosecutor + Arbiter directly, using Run A or Arbiter single verdict)
    y_full = []    # Agent 1 + 2 + 3 (Full Adversarial Debate)

    with open(path, encoding='utf-8') as f:
        for line in f:
            d = json.loads(line)
            gold = d['gold']
            y_gold.append(gold)
            
            c1 = d['prosecutor']['candidate_class']
            y_a1.append(c1)
            
            def_info = d.get('defender') or {}
            concede = def_info.get('concede_charge', True)
            alt = def_info.get('alternative_class', c1)
            
            # Agent 1 + 2:
            # Prosecutor indicts -> Defender evaluates.
            # If Defender concedes -> c1.
            # If Defender challenges -> accept Defender's alternative directly without Arbiter review!
            if concede or alt in ('None', None, ''):
                pred_12 = c1
            else:
                pred_12 = alt
            y_a1_a2.append(pred_12)
            
            # Agent 1 + 3:
            # Prosecutor indicts -> Arbiter reviews directly without Defender's Principle of Charity.
            # In the pipeline, for contested cases, Run A evaluates Option 1 (Cand) vs Option 2 (Alt/Runner-up).
            arb = d.get('arbiter') or {}
            runs = arb.get('permuted_runs')
            if runs:
                # Arbiter evaluated Option 1 (Candidate) vs Option 2
                pred_13 = runs[0].get('prediction', c1)
            else:
                # Uncontested: Arbiter directly verified Candidate
                pred_13 = arb.get('prediction', c1)
            y_a1_a3.append(pred_13)
            
            # Full (Agent 1 + 2 + 3):
            y_full.append(d['prediction'])

    labels = sorted(list(set(y_gold)))
    
    def get_stats(y_pred):
        acc = accuracy_score(y_gold, y_pred)
        f1 = f1_score(y_gold, y_pred, average='macro')
        correct = sum(1 for g, p in zip(y_gold, y_pred) if g.lower() == p.lower())
        rep = classification_report(y_gold, y_pred, output_dict=True)
        return acc, f1, correct, rep

    acc1, f11, c1, rep1 = get_stats(y_a1)
    acc12, f112, c12, rep12 = get_stats(y_a1_a2)
    acc13, f113, c13, rep13 = get_stats(y_a1_a3)
    acc_full, f1_full, c_full, rep_full = get_stats(y_full)

    print(f"=== Results for {path} ===")
    print(f"Total Test Samples: {len(y_gold)}")
    print(f"1. Agent 1 (Prosecutor Only)               : Acc = {acc1*100:.2f}% ({c1}/481), Macro-F1 = {f11*100:.2f}%")
    print(f"2. Agent 1 + 2 (Prosecutor + Defender)     : Acc = {acc12*100:.2f}% ({c12}/481), Macro-F1 = {f112*100:.2f}%")
    print(f"3. Agent 1 + 3 (Prosecutor + Arbiter)      : Acc = {acc13*100:.2f}% ({c13}/481), Macro-F1 = {f113*100:.2f}%")
    print(f"4. Agent 1 + 2 + 3 (Full Adversarial Debate): Acc = {acc_full*100:.2f}% ({c_full}/481), Macro-F1 = {f1_full*100:.2f}%")
    
    print("\n--- Per-Class F1 Breakdown ---")
    print(f"{'Class':26s} | {'Agent 1':>10s} | {'Agent 1+2':>10s} | {'Agent 1+3':>10s} | {'Full (1+2+3)':>12s}")
    print("-" * 75)
    for l in labels:
        f_1 = rep1[l]['f1-score'] * 100
        f_12 = rep12[l]['f1-score'] * 100
        f_13 = rep13[l]['f1-score'] * 100
        f_f = rep_full[l]['f1-score'] * 100
        print(f"{l:26s} | {f_1:9.2f}% | {f_12:9.2f}% | {f_13:9.2f}% | {f_f:11.2f}%")

print(">>> LLAMA-3.3-70B PHASE 1 <<<")
evaluate_combos('outputs/marketplace-classification-adversarial-llama70b-test481-phase1/predictions.jsonl')

print("\n\n>>> GPT-OSS-120B V1 <<<")
evaluate_combos('outputs/marketplace-classification-adversarial-gptoss120b-test481-v1/predictions.jsonl')
