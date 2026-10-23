#!/usr/bin/env python3
"""Script to test API keys and endpoints configured in env2 / .env2.

Tests both:
1. Authentication & endpoint availability (/models)
2. Actual chat completion inference (/chat/completions)

Requires only the Python standard library.
"""

import argparse
import json
import sys
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

# Ensure UTF-8 output on Windows consoles
if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass


def mask_key(key: str) -> str:
    """Mask key for safe display (e.g., nvapi-rIOY...xiE-)."""
    if not key:
        return "<EMPTY>"
    key = key.strip()
    if len(key) <= 10:
        return key[:3] + "..." + key[-2:]
    return key[:8] + "..." + key[-5:]


def parse_env_file(env_path: Path) -> dict[str, str]:
    """Parse key=value pairs from env file, ignoring comments and blank lines."""
    env_vars = {}
    if not env_path.is_file():
        return env_vars

    with open(env_path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            # Remove trailing comments if not quoted
            if "#" in line:
                # simple split on '#' if not inside quotes
                parts = line.split("#", 1)
                line = parts[0].strip()
            if "=" in line:
                key, val = line.split("=", 1)
                val = val.strip().strip("'\"")
                env_vars[key.strip()] = val
    return env_vars


def api_request(url: str, key: str, payload: dict | None = None, timeout: int = 15) -> tuple[int, dict | str]:
    """Perform a GET or POST request to an OpenAI-compatible endpoint."""
    headers = {
        "Authorization": f"Bearer {key}",
        "Accept": "application/json",
    }
    data = None
    if payload is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(payload).encode("utf-8")

    req = Request(url, data=data, headers=headers, method="POST" if data else "GET")
    try:
        start_time = time.monotonic()
        with urlopen(req, timeout=timeout) as resp:
            elapsed = int((time.monotonic() - start_time) * 1000)
            raw = resp.read().decode("utf-8", errors="replace")
            try:
                body = json.loads(raw)
            except Exception:
                body = raw
            return resp.status, body, elapsed
    except HTTPError as e:
        raw_err = e.read().decode("utf-8", errors="replace")
        try:
            err_json = json.loads(raw_err)
        except Exception:
            err_json = raw_err
        return e.code, err_json, 0
    except URLError as e:
        return 0, f"Connection error: {e.reason}", 0
    except Exception as e:
        return -1, str(e), 0


def extract_content(response_payload: dict) -> str:
    """Extract message content or reasoning content from chat completion response."""
    if not isinstance(response_payload, dict):
        return str(response_payload)
    choices = response_payload.get("choices", [])
    if not choices or not isinstance(choices, list):
        return "No choices in response"
    msg = choices[0].get("message", {})
    content = msg.get("content")
    if content:
        return content.strip().replace("\n", " ")
    reasoning = msg.get("reasoning") or msg.get("reasoning_content")
    if reasoning:
        return f"[Reasoning] {str(reasoning).strip().replace(chr(10), ' ')}"
    return "[Empty response]"


def test_provider(
    provider_name: str,
    base_url: str,
    api_key: str,
    default_model: str | None = None,
    test_completion: bool = True,
):
    """Test a provider endpoint: check /models, then test /chat/completions."""
    print(f"\n--- Testing [{provider_name}] ---")
    print(f"Base URL : {base_url}")
    print(f"API Key  : {mask_key(api_key)}")

    if not api_key:
        print("Status   : ⚠️  SKIPPED (No API key provided)")
        return {"status": "SKIPPED", "reason": "No API key"}

    base_url = base_url.rstrip("/")
    models_url = f"{base_url}/models"
    status_code, resp, elapsed = api_request(models_url, api_key)

    if status_code != 200:
        err_msg = resp if isinstance(resp, str) else json.dumps(resp, ensure_ascii=False)
        print(f"Status   : ❌ FAILED (HTTP {status_code} on /models)")
        print(f"Details  : {err_msg[:250]}")
        return {"status": "FAILED", "code": status_code, "error": err_msg}

    # Extract model list
    models = []
    if isinstance(resp, dict):
        models = [m.get("id") for m in resp.get("data", []) if isinstance(m, dict) and "id" in m]

    print(f"Models   : ✅ OK ({len(models)} models available, latency: {elapsed}ms)")
    if models:
        sample_models = models[:4]
        print(f"Examples : {', '.join(sample_models)}")

    if not test_completion:
        return {"status": "SUCCESS", "models_count": len(models)}

    # Determine model to test completion
    model_to_use = default_model
    if not model_to_use:
        # Pick from available models
        for m in models:
            # prefer instruct/chat models
            if any(k in m.lower() for k in ["chat", "instruct", "qwen", "llama", "deepseek", "gpt"]):
                model_to_use = m
                break
        if not model_to_use and models:
            model_to_use = models[0]

    if not model_to_use:
        print("Chat Test: ⚠️  No model found to run completion test")
        return {"status": "SUCCESS", "models_count": len(models)}

    chat_url = f"{base_url}/chat/completions"
    payload = {
        "model": model_to_use,
        "messages": [{"role": "user", "content": "Respond with 'API test success'"}],
        "max_tokens": 100,
    }

    c_status, c_resp, c_elapsed = api_request(chat_url, api_key, payload=payload, timeout=30)
    if c_status == 200:
        reply = extract_content(c_resp)
        print(f"Chat Test: ✅ SUCCESS using model '{model_to_use}' ({c_elapsed}ms)")
        print(f"Reply    : \"{reply[:80]}...\"")
        return {"status": "SUCCESS", "model": model_to_use, "latency_ms": c_elapsed}
    else:
        err_msg = c_resp if isinstance(c_resp, str) else json.dumps(c_resp, ensure_ascii=False)
        # Check specific known errors
        note = ""
        if c_status == 402:
            note = " (Insufficient balance / Hết tiền/credit)"
        elif c_status == 429:
            note = " (Rate limit exceeded / Quá giới hạn gọi API)"
        elif c_status == 401:
            note = " (Unauthorized / Sai API Key)"

        print(f"Chat Test: ❌ FAILED (HTTP {c_status}{note})")
        print(f"Details  : {err_msg[:250]}")
        return {"status": "CHAT_FAILED", "code": c_status, "error": err_msg}


def find_env_file(explicit_path: str | None) -> Path:
    """Find the env file by checking candidate paths."""
    candidates = []
    if explicit_path:
        candidates.append(Path(explicit_path))
    candidates.extend([
        Path(".env2"),
        Path("env2"),
        Path(".env"),
        Path("../.env2"),
        Path("../env2"),
    ])

    for p in candidates:
        if p.is_file():
            return p.resolve()

    return Path(".env2").resolve()


def main():
    parser = argparse.ArgumentParser(description="Test API keys from env2 / .env2 file")
    parser.add_argument("--env", "-e", default=None, help="Path to env2 or .env file (default: .env2 or env2)")
    parser.add_argument("--skip-chat", action="store_true", help="Only test /models endpoint, skip chat completion test")
    parser.add_argument("--all-nvidia-chat", action="store_true", help="Run chat completions for ALL Nvidia keys (1..9), not just key 1")
    args = parser.parse_args()

    env_path = find_env_file(args.env)
    print("=" * 65)
    print("           API CONNECTIVITY & VALIDATION TEST")
    print("=" * 65)
    print(f"Loading environment from: {env_path}")

    if not env_path.is_file():
        print(f"❌ Error: File '{env_path}' not found!")
        print("Please create an 'env2' or '.env2' file in the root directory.")
        return 1

    env = parse_env_file(env_path)
    if not env:
        print("❌ Error: No environment variables could be parsed from the file.")
        return 1

    print(f"Parsed {len(env)} environment keys.")

    results = {}

    # 1. Test Market API (FPT Cloud)
    market_base = env.get("MARKET_API_BASE", "https://mkp-api.fptcloud.com/v1/")
    market_key = env.get("MARKET_API_KEY", "")
    results["MARKET_API"] = test_provider(
        provider_name="Marketplace API (FPT Cloud)",
        base_url=market_base,
        api_key=market_key,
        default_model=env.get("MARKET_MODEL", "FPT.AI-Qwen3.5-35B-A3B"),
        test_completion=not args.skip_chat,
    )

    # 2. Test MiniMax API
    minimax_base = env.get("MINIMAX_BASE_URL", "https://api.minimax.io/v1")
    minimax_key = env.get("MINIMAX_API_KEY", "")
    results["MINIMAX"] = test_provider(
        provider_name="MiniMax API",
        base_url=minimax_base,
        api_key=minimax_key,
        default_model=env.get("MINIMAX_MODEL", "MiniMax-M2.7"),
        test_completion=not args.skip_chat,
    )

    # 3. Test NVIDIA keys (NVIDIA_API_KEY_1 .. NVIDIA_API_KEY_9)
    nvidia_base = env.get("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1")
    nvidia_model = env.get("NVIDIA_MODEL", "openai/gpt-oss-20b")

    print("\n" + "=" * 65)
    print("           TESTING NVIDIA API KEYS (1..9)")
    print("=" * 65)

    nvidia_count = 0
    for i in range(1, 10):
        key_name = f"NVIDIA_API_KEY_{i}"
        key_val = env.get(key_name, "")
        if key_val:
            nvidia_count += 1
            # For Nvidia keys, test chat on key 1 by default, or all if --all-nvidia-chat flag is set
            run_chat = not args.skip_chat and (i == 1 or args.all_nvidia_chat)
            res = test_provider(
                provider_name=f"{key_name}",
                base_url=nvidia_base,
                api_key=key_val,
                default_model=nvidia_model,
                test_completion=run_chat,
            )
            results[key_name] = res

    if nvidia_count == 0:
        # Check single NVIDIA_API_KEY if present
        single_key = env.get("NVIDIA_API_KEY", "")
        if single_key:
            results["NVIDIA_API_KEY"] = test_provider(
                provider_name="NVIDIA_API_KEY",
                base_url=nvidia_base,
                api_key=single_key,
                default_model=nvidia_model,
                test_completion=not args.skip_chat,
            )
        else:
            print("⚠️  No NVIDIA_API_KEY_1..9 found in env file.")

    # 4. Optional 9Router test if present
    router_base = env.get("9ROUTER_API_BASE", "")
    router_key = env.get("9ROUTER_API_KEY", "")
    if router_base and router_key:
        results["9ROUTER"] = test_provider(
            provider_name="9Router API",
            base_url=router_base,
            api_key=router_key,
            default_model=env.get("ROUTER_MODEL"),
            test_completion=not args.skip_chat,
        )

    # Print Summary Table
    print("\n" + "=" * 65)
    print("                       TEST SUMMARY")
    print("=" * 65)
    print(f"{'Provider / Key':<24} | {'Status':<12} | {'Notes / Details'}")
    print("-" * 65)

    total = len(results)
    passed = 0
    for name, res in results.items():
        st = res.get("status", "UNKNOWN")
        if st == "SUCCESS":
            status_str = "✅ PASS"
            passed += 1
            details = f"Latency: {res.get('latency_ms', '-')}ms"
            if "models_count" in res:
                details += f" ({res['models_count']} models)"
        elif st == "CHAT_FAILED":
            status_str = "⚠️ CHAT FAIL"
            code = res.get("code")
            if code == 402:
                details = "HTTP 402: Insufficient balance"
            elif code == 429:
                details = "HTTP 429: Rate limited"
            else:
                details = f"HTTP {code}"
        elif st == "FAILED":
            status_str = "❌ FAIL"
            details = f"HTTP {res.get('code')}"
        elif st == "SKIPPED":
            status_str = "⚪ SKIPPED"
            details = res.get("reason", "")
        else:
            status_str = st
            details = ""

        print(f"{name:<24} | {status_str:<12} | {details}")

    print("-" * 65)
    print(f"Total endpoints tested: {total} | Passed: {passed} | Issues: {total - passed}\n")
    return 0 if (passed > 0 and (total - passed) == 0) else 1


if __name__ == "__main__":
    sys.exit(main())
