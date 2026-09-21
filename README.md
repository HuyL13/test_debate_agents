# CoCoLoFa Unified Multi-Perspective Reasoning

This repo runs three independent fallacy perspectives followed by unified comparative adjudication for the original CoCoLoFa detection and classification tasks.

## Data

Use the upstream CoCoLoFa repository at pinned commit `c39d45fdd57401e1f6cb674f25113dfa0304e734`. The tracked dataset state is only `data/cocolofa/provenance.json`; `train.json`, `dev.json`, and `test.json` are prepared locally and ignored by Git.

```powershell
python scripts/prepare_data.py
python scripts/verify_dataset.py --data-dir data/cocolofa
```

## Environment

Copy `.env.example` to `.env` and set `NVIDIA_API_KEY`. The runner loads `.env`; no shell export is required.

```powershell
cp .env.example .env
python -m pip install -r requirements.txt
```

## Run

```powershell
python -m src.run --config configs/detection.yaml --split dev --limit 1 --output smoke
python -m src.run --config configs/classification.yaml --split dev --limit 1 --output smoke-classification
```

For a true single-LLM zero-shot baseline (one model request per sample, with no
analysts, conflict resolution, or arbiter), run:

```powershell
python -m src.single_llm --config configs/single_llm_detection.yaml --split test --output detection-test-single-llm
python -m src.single_llm --config configs/single_llm_classification.yaml --split test --output classification-test-single-llm
```

Runs are written under `runs/`. Each run contains `manifest.json`, `metrics.json`, `samples.csv`, readable YAML traces under `traces/`, and API metadata under `audit/api_calls.jsonl`. Raw API dumps are disabled unless `TRACE_RAW_API=1`.

## Method

The flow uses three independent initial analysts:

- `structure`: inferential form and mandatory slots
- `goal`: argument function and discourse ownership
- `counterargument`: strongest objection versus strongest defense

Candidate dossiers preserve every proposed and contested interpretation without pairwise elimination. Detection always compares them against an explicit `Non-Fallacious` hypothesis in one final call. Classification shortcuts only a unanimous uncontested singleton; disagreements and recovery use the same comparative adjudicator. There is no voting protocol or resolver tournament.

## Metrics

Detection reports accuracy, positive-class precision/recall/F1, false positive rate, false negative rate, and a confusion matrix. Classification reports accuracy, macro-F1 over all eight CoCoLoFa labels, per-label scores, and an 8x8 confusion matrix.

## Tests

```powershell
pytest -q
```
