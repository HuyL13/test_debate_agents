import json
from pathlib import Path

v4_path = Path("outputs/nvidia-classification-adversarial-llama11b-dev66-v4/predictions.jsonl")
v4_rows = [json.loads(line) for line in v4_path.read_text(encoding="utf-8").strip().split("\n")]

print("=== SAMPLES WHERE DEFENDER CHALLENGED (NOT CONCEDED) ===")
challenged = []
for row in v4_rows:
    sid = row["sample_id"]
    gold = row["gold"]
    final = row["prediction"]
    cand = row.get("prosecutor", {}).get("candidate_class")
    cand_quote = row.get("prosecutor", {}).get("quote")
    defender = row.get("defender", {})
    alt = defender.get("alternative_class")
    concede = defender.get("concede_charge", False)
    alt_quote = defender.get("counter_quote")
    arbiter = row.get("arbiter", {})
    stop_reason = row.get("stop_reason")
    
    if alt and alt != "None" and not concede:
        challenged.append((sid, gold, cand, alt, final, stop_reason, cand_quote, alt_quote, arbiter))

print(f"Total challenged: {len(challenged)}")
for sid, gold, cand, alt, final, stop_reason, cand_quote, alt_quote, arbiter in challenged:
    print(f"\nSample {sid}:")
    print(f"  Gold:        {gold}")
    print(f"  Prosecutor:  {cand} (quote: '{cand_quote}')")
    print(f"  Defender:    {alt} (counter-quote: '{alt_quote}')")
    print(f"  Arbiter:     {final} (stop_reason: {stop_reason})")
    print(f"  Arbiter run details: {arbiter}")

print("\n=== WHY DID DEFENDER CONCEDE IN OTHER 59 SAMPLES? ===")
# Let's inspect a few conceded samples to see if Defender explicitly conceded or normalized
concede_types = {"explicit_true": 0, "alt_none": 0, "alt_same_as_cand": 0, "vetoed_by_cue": 0}
for row in v4_rows:
    defender = row.get("defender", {})
    alt = defender.get("alternative_class")
    concede = defender.get("concede_charge", False)
    cand = row.get("prosecutor", {}).get("candidate_class")
    
    # Check deliberation logs if any
    delib = row.get("deliberation", [])
    
    if concede or alt == "None":
        if concede:
            concede_types["explicit_true"] += 1
        if alt == "None":
            concede_types["alt_none"] += 1
        if alt == cand:
            concede_types["alt_same_as_cand"] += 1

print("Concede stats:", concede_types)
