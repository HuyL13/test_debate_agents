# Train from GitHub in one Kaggle cell

Enable GPU T4 and Internet. No input Dataset is required. Replace the API key
placeholder locally and do not publish a notebook containing your key.
The cell clones the dedicated branch, downloads pinned public CoCoLoFa splits
and tokenizer, verifies their checksums, tests CUDA PPO plus real frozen BGE,
and trains the full3168 classification samples for one epoch.
BGE/actor/critic run on cuda; the LLM remains NVIDIA API. Reward step cost .01,
output-token cost .00001, call cost0. First startup downloads BGE (~440MB).
Use a fresh Kaggle session when switching from a ZIP/older source.

The final cell in your chat is pinned to the reviewed Git commit; the example
below follows the branch. Preserve the printed source commit for reproducibility.
Resume only checkpoints with matching source/config/model. Save the entire parent
run directory (including best.pt) and restore it when resuming. --epochs is a
total target, not additional epochs. Session termination may prevent finally
from running; save/download last.pt and output before your session expires.

```python
import os, sys, subprocess, tarfile
from pathlib import Path

API_KEY = "YOUR_NVIDIA_API_KEY_HERE"
REPO = "https://github.com/HuyL13/test_debate_agents.git"
BRANCH = "feat/courtroom-kaggle-bge"
RESUME = None  # Optional: path to last.pt created by this exact source/config.
PROJECT = Path("/kaggle/working/courtroom-github")
assert API_KEY.strip() and API_KEY != "YOUR_NVIDIA_API_KEY_HERE", "Fill in your NVIDIA API key"

def run(*args):
    subprocess.run(list(args), check=True)

if not PROJECT.exists():
    run("git", "clone", "--single-branch", "--branch", BRANCH, REPO, str(PROJECT))
os.chdir(PROJECT)
print("Source commit:", subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip())
run(sys.executable, "-m", "pip", "install", "-q", "-r", "requirements-kaggle.txt")
os.environ["NVIDIA_API_KEY"] = API_KEY.strip()
os.environ["NVIDIA_BASE_URL"] = "https://integrate.api.nvidia.com/v1"
os.environ["NVIDIA_MODEL"] = "meta/llama-3.2-11b-vision-instruct"
os.environ["PYTHONUNBUFFERED"] = "1"
import torch
assert torch.cuda.is_available(), "Enable GPU T4 in Kaggle Settings"
run(sys.executable, "-u", "scripts/prepare_courtroom_kaggle.py", "--config", "configs/courtroom_rl.v4.kaggle.yaml")
run(sys.executable, "-u", "scripts/check_kaggle_gpu.py", "--config", "configs/courtroom_rl.v4.kaggle.yaml")
cmd = [sys.executable, "-u", "-m", "src.courtroom_rl.runner", "train",
       "--config", "configs/courtroom_rl.v4.kaggle.yaml", "--epochs", "1",
       "--batch-size", "8", "--workers", "4", "--dev-limit", "66", "--dev-every", "10",
       "--warmup-episodes", "8", "--seed", "0", "--log-steps"]
if RESUME:
    cmd += ["--resume", RESUME]
try:
    run(*cmd)
finally:
    output = Path("/kaggle/working/courtroom-training-output.tar.gz")
    with tarfile.open(output, "w:gz") as tar:
        for relative in ["runs", "cache/courtroom_rl/assessor.joblib"]:
            path = PROJECT / relative
            if path.exists():
                tar.add(path, arcname="courtroom-github/" + relative)
    print("Download:", output)
```

Development set update (2026-10-15): new main/pilot/Kaggle runs default to all66 pinned dialectical diagnostic cases, originally selected from official test errors. Official train/dev/test artifacts stay unchanged. This development use exposes these test cases; do not report them as fresh held-out test. An explicit --dev-limit still subsets the configured development set. Older checkpoints have different source/config/dev-selection contracts and do not resume directly.

Parallel V4 update: --workers4 collects four independent episodes concurrently, including warmup and dev. PPO waits for the entire batch and then updates once. Each episode owns its API client/budget and sampling generator; changing worker count is safe at a checkpoint boundary. API logs include episode/sample IDs. Start with4; use --workers2 if the provider persistently rate-limits.
