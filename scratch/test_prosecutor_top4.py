import json
import os
import time
from urllib.request import Request, urlopen
from pathlib import Path

# Load env
env_path = Path('.env')
if env_path.exists():
    for line in env_path.read_text(encoding='utf-8').splitlines():
        if '=' in line and not line.startswith('#'):
            k, v = line.split('=', 1)
            os.environ.setdefault(k.strip(), v.strip())

api_key = os.environ.get('MARKET_API_KEY')
base_url = 'https://mkp-api.fptcloud.com/v1/chat/completions'

import sys
sys.path.insert(0, '.')
from src.data.loader import load_split
samples = load_split('data/cocolofa/test.json')
gold_samples = [s for s in samples if s.fallacy != 'none']
s = gold_samples[0]

system_prompt = """You are an expert argumentation logician evaluating logical fallacies in online discourse using the 8-class closed CoCoLoFa taxonomy:
1. Appeal to Authority
2. Appeal to Majority
3. Appeal to Nature
4. Appeal to Tradition
5. Appeal to Worse Problems
6. False Dilemma
7. Hasty Generalization
8. Slippery Slope

Analyze the TARGET comment and identify the TOP-4 most plausible fallacy classes from the taxonomy, ranked in descending order of likelihood from Rank 1 (best match) to Rank 4.

Return ONLY a valid JSON object matching this schema:
{
  "top_4": [
    {"rank": 1, "class": "<Class 1>", "quote": "<exact quote from target comment>", "defect_mechanism": "<why this defect applies>"},
    {"rank": 2, "class": "<Class 2>", "quote": "<exact quote from target comment>", "defect_mechanism": "<competing mechanism>"},
    {"rank": 3, "class": "<Class 3>", "quote": "<quote or key phrase>", "defect_mechanism": "<mechanism>"},
    {"rank": 4, "class": "<Class 4>", "quote": "<quote or key phrase>", "defect_mechanism": "<mechanism>"}
  ]
}
All 4 classes MUST be distinct and chosen strictly from the 8 CoCoLoFa classes."""

user_prompt = f"""News Article Title: {s.title}
Parent Comment: {s.parent_comment or 'None'}
TARGET Comment: {s.comment}

Analyze the TARGET comment and return the TOP-4 ranked candidate fallacy classes in JSON."""

payload = {
    'model': 'Llama-3.3-70B-Instruct',
    'messages': [
        {'role': 'system', 'content': system_prompt},
        {'role': 'user', 'content': user_prompt}
    ],
    'temperature': 0.1,
    'max_tokens': 1024
}

t0 = time.time()
req = Request(base_url, data=json.dumps(payload).encode('utf-8'),
              headers={'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'},
              method='POST')

with urlopen(req, timeout=60) as resp:
    data = json.loads(resp.read().decode('utf-8'))

latency = time.time() - t0
print(f"Latency: {latency:.2f}s")
content = data['choices'][0]['message']['content']
print("Response content:")
print(content)
