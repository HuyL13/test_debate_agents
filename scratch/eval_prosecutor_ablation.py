import json
from sklearn.metrics import classification_report, accuracy_score, f1_score

def eval_prosecutor_only(path):
    y_true = []
    y_pros = []
    y_final = []
    
    with open(path, encoding='utf-8') as f:
        for line in f:
            d = json.loads(line)
            gold = d['gold']
            pros = d['prosecutor']['candidate_class']
            final = d['prediction']
            
            y_true.append(gold)
            y_pros.append(pros)
            y_final.append(final)
            
    acc_pros = accuracy_score(y_true, y_pros)
    f1_pros = f1_score(y_true, y_pros, average='macro')
    
    acc_final = accuracy_score(y_true, y_final)
    f1_final = f1_score(y_true, y_final, average='macro')
    
    print(f"=== {path} ===")
    print(f"Prosecutor Only (Single Agent) : Acc = {acc_pros*100:.2f}%, Macro-F1 = {f1_pros*100:.2f}% ({sum(1 for t, p in zip(y_true, y_pros) if t.lower() == p.lower())}/{len(y_true)})")
    print(f"Full Adversarial Multi-Agent   : Acc = {acc_final*100:.2f}%, Macro-F1 = {f1_final*100:.2f}% ({sum(1 for t, p in zip(y_true, y_final) if t.lower() == p.lower())}/{len(y_true)})")
    print(f"Adversarial Multi-Agent Gain   : Acc = {(acc_final - acc_pros)*100:+.2f}%, Macro-F1 = {(f1_final - f1_pros)*100:+.2f}%")
    
    rep_pros = classification_report(y_true, y_pros, output_dict=True)
    rep_final = classification_report(y_true, y_final, output_dict=True)
    labels = sorted(list(set(y_true)))
    print("\nPer-class F1 (Prosecutor Only -> Full Adversarial):")
    for l in labels:
        f_p = rep_pros[l]['f1-score'] * 100
        f_f = rep_final[l]['f1-score'] * 100
        print(f"  - {l:24s}: {f_p:.2f}% -> {f_f:.2f}% ({(f_f - f_p):+.2f}%)")

print(">>> LLAMA-3.3-70B PHASE 1 <<<")
eval_prosecutor_only('outputs/marketplace-classification-adversarial-llama70b-test481-phase1/predictions.jsonl')

print("\n\n>>> GPT-OSS-120B V1 <<<")
eval_prosecutor_only('outputs/marketplace-classification-adversarial-gptoss120b-test481-v1/predictions.jsonl')
