import json
from pathlib import Path

lines = Path('outputs/marketplace-classification-adversarial-llama70b-test481-v1/raw_calls.jsonl').read_text(encoding='utf-8').strip().split('\n')
sample_calls = []
for line in lines[-25:]:
    d = json.loads(line)
    if d.get('metadata', {}).get('sample_id') == '442:6722':
        sample_calls.append(d)

print(f'Found {len(sample_calls)} calls for 442:6722')
for i, c in enumerate(sample_calls):
    meta = c.get('metadata', {})
    print(f"\n--- Call {i}: role={meta.get('role')} stage={meta.get('stage')} attempt={meta.get('attempt', 1)} ---")
    resp = c.get('response', {})
    choices = resp.get('choices', [])
    if choices:
        choice = choices[0]
        print('finish_reason:', choice.get('finish_reason'))
        msg = choice.get('message', {})
        print('content:', repr(msg.get('content')))
        print('refusal:', msg.get('refusal'))
        print('tool_calls:', msg.get('tool_calls'))
    else:
        print('No choices! Response:', resp)
    if 'validation_error' in c:
        print('validation_error:', c.get('validation_error'))
    if 'error' in c:
        print('client error field:', c.get('error'))
