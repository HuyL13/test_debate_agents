import os
import urllib.request
import urllib.error
import json

key = os.environ.get('NVIDIA_API_KEY')
print("=== NVIDIA API Key Diagnostic ===")
print("NVIDIA_API_KEY present:", bool(key))
if not key:
    print("ERROR: NVIDIA_API_KEY environment variable is not set in this shell.")
    print("Run: $env:NVIDIA_API_KEY='nvapi-...' before running experiments.")
else:
    print(f"Key preview: {key[:8]}... (length: {len(key)})")
    
    # 1. Test /v1/models endpoint
    print("\n1. Testing /v1/models endpoint...")
    req_models = urllib.request.Request(
        "https://integrate.api.nvidia.com/v1/models",
        headers={"Authorization": f"Bearer {key}"}
    )
    try:
        with urllib.request.urlopen(req_models, timeout=15) as resp:
            print(f"   Status: {resp.status} OK (Authentication successful!)")
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8', errors='replace')
        print(f"   FAILED HTTP {e.code}: {body}")
    except Exception as e:
        print(f"   FAILED: {e}")

    # 2. Test completion with meta/llama-3.2-11b-vision-instruct
    print("\n2. Testing chat completion with meta/llama-3.2-11b-vision-instruct...")
    payload = json.dumps({
        "model": "meta/llama-3.2-11b-vision-instruct",
        "messages": [{"role": "user", "content": "Hello, answer in 3 words."}],
        "max_tokens": 10
    }).encode('utf-8')
    req_chat = urllib.request.Request(
        "https://integrate.api.nvidia.com/v1/chat/completions",
        data=payload,
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json"
        }
    )
    try:
        with urllib.request.urlopen(req_chat, timeout=20) as resp:
            print(f"   Status: {resp.status} OK")
            data = json.loads(resp.read().decode('utf-8'))
            print("   Response:", data['choices'][0]['message']['content'])
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8', errors='replace')
        print(f"   FAILED HTTP {e.code}: {body}")
    except Exception as e:
        print(f"   FAILED: {e}")
