import json
from pathlib import Path

raw_calls = [json.loads(line) for line in Path('outputs/marketplace-classification-adversarial-llama70b-dev66-v1/raw_calls.jsonl').read_text(encoding='utf-8').strip().split('\n')]
print(f"Total raw calls logged: {len(raw_calls)}")
for i in range(-5, 0):
    c = raw_calls[i]
    print(f"\n--- Call {len(raw_calls)+i+1} (attempt {c.get('attempt')}) ---")
    print("Valid:", c.get("valid"))
    print("Role:", c.get("metadata", {}).get("role"))
    print("Sample ID:", c.get("metadata", {}).get("sample_id"))
    print("Error:", c.get("error"))
    content = c.get('response', {}).get('choices', [{}])[0].get('message', {}).get('content', '')
    print("Content preview:", repr(content[:300]))
