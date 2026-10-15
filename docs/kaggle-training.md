# Kaggle T4 training

Upload outputs/courtroom-kaggle.zip as a private Kaggle Dataset and attach it to a notebook.
Import docs/kaggle-training.ipynb, select GPU T4, enable Internet and enable the NVIDIA_API_KEY Secret.
Run cells in order. The notebook checks CUDA offline before paid API training.
Only one GPU is used: these small attention actor/critic networks do not need multi-GPU.
The LLM remains remote; GPU does not accelerate API latency .
The Kaggle config enables semantic observations (frozen BGE-base-en-v1.5 BERT embeddings + cosine relevance on CUDA), and restores step cost .01 and output-token cost .00001 (call cost0), with batch8 and existing PPO settings.
Full official train is used (3168 samples), with diagnostic dev66 every10 updates.

Resume only a checkpoint from this exact source/config/model. The RESUME variable in the
training cell accepts last.pt. Preserve its parent run directory including best.pt.
Epochs is a total target: use2 to extend a completed epoch1 run to2 epochs.
Old Windows checkpoints have a different source/config and cannot be resumed by this package.
Save/download notebook outputs before session termination; checkpoint writes alone do not
make ephemeral session storage persistent. A final cell creates a downloadable recovery bundle.
The bundle excludes credentials and old runs. V4 uses terminal reward without an assessor.
Do not replace the source/config midway through a run.

Copy-paste cells (also available in the notebook):

```python
import os, sys, shutil, subprocess, zipfile
from pathlib import Path
from kaggle_secrets import UserSecretsClient

PROJECT = Path('/kaggle/working/cocolofa_pard')
archives = list(Path('/kaggle/input').rglob('courtroom-kaggle.zip'))
if not PROJECT.exists():
    if len(archives) == 1:
        with zipfile.ZipFile(archives[0]) as z:
            z.extractall('/kaggle/working')
    else:
        candidates = list(Path('/kaggle/input').rglob('courtroom_rl.kaggle.yaml'))
        assert len(candidates) == 1, 'Attach the courtroom-kaggle Dataset first'
        shutil.copytree(candidates[0].parent.parent, PROJECT)
os.chdir(PROJECT)
subprocess.run([sys.executable, '-m', 'pip', 'install', '-q', '-r', 'requirements-kaggle.txt'], check=True)
os.environ['NVIDIA_API_KEY'] = UserSecretsClient().get_secret('NVIDIA_API_KEY')
os.environ['NVIDIA_BASE_URL'] = 'https://integrate.api.nvidia.com/v1'
os.environ['NVIDIA_MODEL'] = 'meta/llama-3.2-11b-vision-instruct'
os.environ['PYTHONUNBUFFERED'] = '1'
import torch
assert torch.cuda.is_available(), 'Enable GPU T4 in Notebook Settings'
print('PPO device:', torch.cuda.get_device_name(0), '| LLM: NVIDIA API')
```

```python
# Real frozen BGE + V4 CUDA rollout/update/checkpoint, no API calls.
subprocess.run([sys.executable, '-u', 'scripts/check_kaggle_gpu.py', '--config', 'configs/courtroom_rl.v4.kaggle.yaml'], check=True)
```

```python
# First run: None. To resume, set the path to YOUR Kaggle last.pt.
# Attach saved output as a Dataset if resuming in a new session.
RESUME = None
# Example: RESUME = '/kaggle/input/my-training-output/cocolofa_pard/runs/courtroom-v4-.../last.pt'
cmd = [sys.executable, '-u', '-m', 'src.courtroom_rl.runner', 'train',
       '--config', 'configs/courtroom_rl.v4.kaggle.yaml',
       '--epochs', '1', '--batch-size', '8', '--dev-limit', '66',
       '--dev-every', '10', '--warmup-episodes', '8', '--seed', '0', '--log-steps']
if RESUME:
    # Copy the run directory so inherited best.pt and its provenance travel too.
    source = Path(RESUME).resolve()
    destination = PROJECT / 'resume_inputs' / source.parent.name
    if not destination.exists():
        shutil.copytree(source.parent, destination)
    cmd += ['--resume', str(destination / source.name)]
subprocess.run(cmd, check=True)
```

```python
# Run after training or interrupting: create a small downloadable recovery bundle.
# Includes all run metadata, last.pt/best.pt, logs and assessor cache, no API key.
import tarfile
artifact = Path('/kaggle/working/courtroom-training-output.tar.gz')
with tarfile.open(artifact, 'w:gz') as tar:
    for relative in ['runs', 'cache/courtroom_rl/assessor.joblib']:
        path = PROJECT / relative
        if path.exists():
            tar.add(path, arcname='cocolofa_pard/' + relative)
print('Saved:', artifact)
```
Development set update (2026-10-15): new main/pilot/Kaggle runs default to all66 pinned dialectical diagnostic cases, originally selected from official test errors. Official train/dev/test artifacts stay unchanged. This development use exposes these test cases; do not report them as fresh held-out test. An explicit --dev-limit still subsets the configured development set. Older checkpoints have different source/config/dev-selection contracts and do not resume directly.
