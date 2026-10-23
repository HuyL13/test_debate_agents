import json
from collections import Counter

def analyze_permutation(path):
    print(f"=== Analyzing {path} ===")
    total_samples = 0
    conceded_samples = 0
    contested_samples = 0
    
    agreed_cand = 0
    agreed_alt = 0
    disagreed = 0
    
    disagreed_cases = []
    
    # Track accuracies
    actual_correct = 0
    run_a_correct = 0
    run_b_correct = 0
    always_cand_correct = 0 # if we never flipped (prosecutor only)
    
    with open(path, encoding='utf-8') as f:
        for line in f:
            d = json.loads(line)
            total_samples += 1
            gold = d['gold']
            actual_pred = d['prediction']
            if actual_pred.lower() == gold.lower():
                actual_correct += 1
                
            arbiter = d.get('arbiter') or {}
            runs = arbiter.get('permuted_runs')
            
            cand = d.get('prosecutor', {}).get('candidate_class')
            alt = (d.get('defender') or {}).get('alternative_class')
            
            if not runs:
                conceded_samples += 1
                # If no runs (conceded), run_a and run_b would just be cand
                if cand.lower() == gold.lower():
                    run_a_correct += 1
                    run_b_correct += 1
                    always_cand_correct += 1
                continue
                
            contested_samples += 1
            pred_a = runs[0].get('prediction')
            pred_b = runs[1].get('prediction')
            
            if cand.lower() == gold.lower():
                always_cand_correct += 1
            if pred_a.lower() == gold.lower():
                run_a_correct += 1
            if pred_b.lower() == gold.lower():
                run_b_correct += 1
                
            if pred_a == pred_b:
                if pred_a == alt:
                    agreed_alt += 1
                else:
                    agreed_cand += 1
            else:
                disagreed += 1
                disagreed_cases.append({
                    'sample_id': d['sample_id'],
                    'gold': gold,
                    'cand': cand,
                    'alt': alt,
                    'pred_a': pred_a,
                    'pred_b': pred_b,
                    'actual_pred': actual_pred,
                    'target_comment': d.get('comment', ''),
                    'reason_a': runs[0].get('content', ''),
                    'reason_b': runs[1].get('content', '')
                })
                
    print(f"Total test samples: {total_samples}")
    print(f"Fast-path Conceded: {conceded_samples} ({conceded_samples/total_samples*100:.1f}%)")
    print(f"Contested (Arbiter called): {contested_samples} ({contested_samples/total_samples*100:.1f}%)")
    print(f"  - Both runs agreed on Candidate: {agreed_cand}")
    print(f"  - Both runs agreed on Alternative (Flipped): {agreed_alt}")
    print(f"  - Disagreed due to Order Bias: {disagreed}")
    print("\nAccuracy Comparison:")
    print(f"  - With Dual-Run Order Permutation + Unanimous Rule (Actual): {actual_correct}/{total_samples} ({actual_correct/total_samples*100:.2f}%)")
    print(f"  - If Run A alone (Single pass): {run_a_correct}/{total_samples} ({run_a_correct/total_samples*100:.2f}%)")
    print(f"  - If Run B alone (Single pass reversed): {run_b_correct}/{total_samples} ({run_b_correct/total_samples*100:.2f}%)")
    print(f"  - If Always Uphold Candidate (No Arbiter flip): {always_cand_correct}/{total_samples} ({always_cand_correct/total_samples*100:.2f}%)")
    
    print("\nDetailed Disagreement Cases Analysis:")
    saved_by_unanimous = 0
    hurt_by_unanimous = 0
    for case in disagreed_cases:
        sid = case['sample_id']
        gold = case['gold']
        cand = case['cand']
        alt = case['alt']
        pred_a = case['pred_a']
        pred_b = case['pred_b']
        actual = case['actual_pred']
        
        # In our unanimous rule, actual is cand
        if actual.lower() == gold.lower():
            saved_by_unanimous += 1
            status = "[SAVED] Unanimous rule protected Candidate (CORRECT) against flaky Alternative!"
        else:
            hurt_by_unanimous += 1
            status = "[MISSED] Gold was Alternative, but order disagreement caused fallback to Candidate."
        print(f"Case {sid} | Gold: '{gold}' | Cand: '{cand}' | Alt: '{alt}'")
        print(f"   Run A (Opt1=Cand, Opt2=Alt): -> '{pred_a}'")
        print(f"   Run B (Opt1=Alt, Opt2=Cand): -> '{pred_b}'")
        print(f"   Verdict: '{actual}' -> {status}")
        print("---")
        
    print(f"\nSummary of Disagreed Cases ({disagreed} total):")
    print(f"  - Saved by Unanimous Rule (Candidate was Gold): {saved_by_unanimous}")
    print(f"  - Missed (Alternative was Gold): {hurt_by_unanimous}")
    return disagreed_cases

print(">>> CHECKING PHASE 1 RUN <<<")
analyze_permutation('outputs/marketplace-classification-adversarial-llama70b-test481-phase1/predictions.jsonl')

print("\n\n>>> CHECKING V1 RUN <<<")
analyze_permutation('outputs/marketplace-classification-adversarial-llama70b-test481-v1/predictions.jsonl')
