import os
import json
import urllib.request
from urllib.error import HTTPError, URLError

def main():
    key = os.environ.get('NVIDIA_API_KEY')
    if not key:
        print("ERROR: NVIDIA_API_KEY is not set in your environment.")
        print("Run: $env:NVIDIA_API_KEY='your_key_here' first.")
        return 1

    url = 'https://integrate.api.nvidia.com/v1/models'
    req = urllib.request.Request(url, headers={'Authorization': f'Bearer {key}'})
    try:
        with urllib.request.urlopen(req, timeout=15) as res:
            data = json.loads(res.read().decode('utf-8'))
            models = sorted([m['id'] for m in data.get('data', [])])
            print(f"Total available models: {len(models)}\n")
            print("--- Popular Text Generation Models ---")
            for m in models:
                if any(k in m.lower() for k in ['llama', 'qwen', 'mistral', 'gpt', 'nemotron', 'deepseek']):
                    print(f"  {m}")
            print("\nUse any of the above names with --model <model_id>")
            return 0
    except HTTPError as e:
        print(f"HTTP Error {e.code}: {e.read().decode('utf-8')}")
        return 1
    except URLError as e:
        print(f"Connection Error: {e}")
        return 1

if __name__ == '__main__':
    raise SystemExit(main())
