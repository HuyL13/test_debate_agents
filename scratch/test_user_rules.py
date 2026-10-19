import json
from pathlib import Path

v3_dir = Path("outputs/nvidia-classification-adversarial-llama11b-dev66-v3/samples")
traces = [json.loads(p.read_text(encoding="utf-8")) for p in v3_dir.glob("*.json")]

print(f"Total traces: {len(traces)}")

# 1. Check how many times alt == candidate
alt_eq_cand = []
for t in traces:
    p_cand = t.get("prosecutor", {}).get("candidate_class")
    d_alt = t.get("defender", {}).get("alternative_class")
    d_concede = t.get("defender", {}).get("concede_charge")
    if not d_concede and d_alt == p_cand:
        alt_eq_cand.append(t)

print(f"1. Defender set concede=False but alternative_class == candidate_class: {len(alt_eq_cand)} cases")
for t in alt_eq_cand:
    print(f"   - [{t['sample_id']}] Gold={t['gold']}, Pros Cand={t['prosecutor']['candidate_class']}, Final={t['prediction']}")

# 2. Check how many times counter_quote was identical to candidate quote
ident_quote = []
for t in traces:
    pq = t.get("prosecutor", {}).get("quote", "").strip().lower()
    dq = t.get("defender", {}).get("counter_quote", "").strip().lower()
    d_concede = t.get("defender", {}).get("concede_charge")
    if not d_concede and pq and dq and (pq == dq or pq in dq or dq in pq):
        ident_quote.append((t["sample_id"], t["gold"], t["prosecutor"]["candidate_class"], t["defender"]["alternative_class"], t["prediction"]))

print(f"\n2. Defender counter_quote identical or substring of candidate quote: {len(ident_quote)} cases")
for item in ident_quote[:10]:
    print(f"   - [{item[0]}] Gold={item[1]}, Cand={item[2]}, Alt={item[3]}, Final={item[4]}")

# 3. Check length of counter_quote (< 5 words)
short_quote = []
for t in traces:
    dq = t.get("defender", {}).get("counter_quote", "").strip()
    d_concede = t.get("defender", {}).get("concede_charge")
    if not d_concede and len(dq.split()) < 5:
        short_quote.append((t["sample_id"], dq))
print(f"\n3. Defender counter_quote < 5 words: {len(short_quote)} cases")
for item in short_quote:
    print(f"   - [{item[0]}] Quote: '{item[1]}'")
