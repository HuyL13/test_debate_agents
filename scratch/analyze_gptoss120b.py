import json
from pathlib import Path

path = Path("outputs/marketplace-classification-adversarial-gptoss120b-dev66-v1/predictions.jsonl")
rows = [json.loads(line) for line in path.read_text(encoding="utf-8").strip().split("\n")]

prosecutor_correct = 0
final_correct = 0

kept_correct = []
flipped_wrong = []
flipped_correct = []
flipped_still_wrong = []
kept_wrong = []

concede_count = 0
permuted_disagree_count = 0

for row in rows:
    sid = row["sample_id"]
    gold = row["gold"]
    final = row["prediction"]
    
    prosecutor = row.get("prosecutor", {})
    cand = prosecutor.get("candidate_class")
    cand_quote = prosecutor.get("quote")
    
    defender = row.get("defender", {})
    alt = defender.get("alternative_class")
    concede = defender.get("concede_charge", False) or (alt == "None")
    if concede:
        concede_count += 1
        
    arbiter = row.get("arbiter", {})
    permuted = arbiter.get("permuted_runs", [])
    if len(permuted) == 2 and permuted[0].get("prediction") != permuted[1].get("prediction"):
        permuted_disagree_count += 1

    p_corr = (cand == gold)
    f_corr = (final == gold)
    
    if p_corr:
        prosecutor_correct += 1
        if f_corr:
            kept_correct.append((sid, gold, cand, alt, final))
        else:
            flipped_wrong.append((sid, gold, cand, alt, final))
    else:
        if f_corr:
            flipped_correct.append((sid, gold, cand, alt, final))
        else:
            if cand != final:
                flipped_still_wrong.append((sid, gold, cand, alt, final))
            else:
                kept_wrong.append((sid, gold, cand, alt, final))
                
    if f_corr:
        final_correct += 1

print("=== GPT-OSS-120B DEBATE ANALYSIS ===")
print(f"Total samples: {len(rows)}")
print(f"Prosecutor Accuracy: {prosecutor_correct}/66 ({prosecutor_correct/66*100:.2f}%)")
print(f"Final V4 Accuracy:   {final_correct}/66 ({final_correct/66*100:.2f}%)")
print(f"Net Gain from Debate: {final_correct - prosecutor_correct:+d} samples")

print(f"\nDefender Concedes: {concede_count}/66")
print(f"Order Permutation Disagreements: {permuted_disagree_count}/66")

print(f"\nWhen Prosecutor was CORRECT ({len(kept_correct) + len(flipped_wrong)} cases):")
print(f"  - Kept Correct (Protected): {len(kept_correct)}")
print(f"  - Flipped to Wrong (Harmful flip): {len(flipped_wrong)}")

print(f"\nWhen Prosecutor was WRONG ({len(flipped_correct) + len(flipped_still_wrong) + len(kept_wrong)} cases):")
print(f"  - Flipped to Correct (Beneficial flip): {len(flipped_correct)}")
print(f"  - Flipped to another Wrong: {len(flipped_still_wrong)}")
print(f"  - Kept Wrong (Unchanged): {len(kept_wrong)}")

print("\n--- BENEFICIAL FLIPS ---")
for item in flipped_correct:
    print(f"  {item[0]}: Gold='{item[1]}' | Cand='{item[2]}' -> Alt='{item[3]}' -> Final='{item[4]}'")

print("\n--- HARMFUL FLIPS ---")
for item in flipped_wrong:
    print(f"  {item[0]}: Gold='{item[1]}' | Cand='{item[2]}' -> Alt='{item[3]}' -> Final='{item[4]}'")
