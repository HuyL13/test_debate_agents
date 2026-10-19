import json
from pathlib import Path

# Load V4 predictions
v4_path = Path("outputs/nvidia-classification-adversarial-llama11b-dev66-v4/predictions.jsonl")
v4_rows = [json.loads(line) for line in v4_path.read_text(encoding="utf-8").strip().split("\n")]

# Load V3 predictions if exists
v3_path = Path("outputs/nvidia-classification-adversarial-llama11b-dev66-v3/predictions.jsonl")
v3_rows = {json.loads(line)["sample_id"]: json.loads(line) for line in v3_path.read_text(encoding="utf-8").strip().split("\n")}

print(f"Total samples loaded in V4: {len(v4_rows)}")

# Let's inspect the keys and structure of a sample
sample0 = v4_rows[0]
print("Keys in sample:", list(sample0.keys()))
if "adversarial_debate" in sample0:
    print("Debate keys:", list(sample0["adversarial_debate"].keys()))

# Analyze Prosecutor vs Defender vs Arbiter
prosecutor_correct = 0
final_correct = 0

kept_correct = []
flipped_wrong = []
flipped_correct = []
flipped_still_wrong = []
kept_wrong = []

concede_count = 0
permuted_disagree_count = 0
cue_veto_count = 0

for row in v4_rows:
    sid = row["sample_id"]
    gold = row["gold"]
    final = row["prediction"]
    
    prosecutor = row.get("prosecutor", {})
    cand = prosecutor.get("candidate_class")
    cand_quote = prosecutor.get("quote")
    
    defender = row.get("defender", {})
    alt = defender.get("alternative_class")
    def_quote = defender.get("counter_quote")
    concede = defender.get("concede_charge", False) or (alt == "None")
    if concede:
        concede_count += 1
        
    arbiter = row.get("arbiter", {})
    run_a = arbiter.get("run_a", {}).get("prediction")
    run_b = arbiter.get("run_b", {}).get("prediction")
    if run_a and run_b and run_a != run_b:
        permuted_disagree_count += 1
        
    validation = row.get("validation", {})
    if validation.get("vetoed_by_cue", False) or validation.get("normalized_concede", False):
        cue_veto_count += 1

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

print("\n--- RESULTS OVERVIEW ---")
print(f"Prosecutor Accuracy: {prosecutor_correct}/66 ({prosecutor_correct/66*100:.2f}%)")
print(f"Final V4 Accuracy:   {final_correct}/66 ({final_correct/66*100:.2f}%)")
print(f"Net Gain from Debate: {final_correct - prosecutor_correct:+d} samples")

print("\n--- FLIP BREAKDOWN ---")
print(f"When Prosecutor was CORRECT ({len(kept_correct) + len(flipped_wrong)} cases):")
print(f"  - Kept Correct (Protected): {len(kept_correct)}")
print(f"  - Flipped to Wrong (Harmful flip): {len(flipped_wrong)}")

print(f"\nWhen Prosecutor was WRONG ({len(flipped_correct) + len(flipped_still_wrong) + len(kept_wrong)} cases):")
print(f"  - Flipped to Correct (Beneficial flip): {len(flipped_correct)}")
print(f"  - Flipped to another Wrong: {len(flipped_still_wrong)}")
print(f"  - Kept Wrong (Unchanged): {len(kept_wrong)}")

print(f"\nDefender Concedes: {concede_count}/66")
print(f"Order Permutation Disagreements (Challenger failed burden): {permuted_disagree_count}/66")

print("\n--- DETAILS OF BENEFICIAL FLIPS (Flipped to Correct) ---")
for sid, gold, cand, alt, final in flipped_correct:
    print(f"  Sample {sid}: Gold='{gold}' | Prosecutor='{cand}' -> Defender Alt='{alt}' -> Final='{final}'")

print("\n--- DETAILS OF HARMFUL FLIPS (Flipped to Wrong) ---")
for sid, gold, cand, alt, final in flipped_wrong:
    print(f"  Sample {sid}: Gold='{gold}' | Prosecutor='{cand}' -> Defender Alt='{alt}' -> Final='{final}'")
