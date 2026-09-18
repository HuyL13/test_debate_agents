# CoCoLoFa Conflict-Guided Reasoning

This repo runs one active research flow for the original CoCoLoFa detection and classification tasks: Conflict-Guided Multi-Agent Fallacy Reasoning.

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

Runs are written under `runs/`. Each run contains `manifest.json`, `metrics.json`, `samples.csv`, readable YAML traces under `traces/`, and API metadata under `audit/api_calls.jsonl`. Raw API dumps are disabled unless `TRACE_RAW_API=1`.

## Method

The flow uses three independent initial analysts:

- `scheme`
- `enthymeme`
- `critical`

A deterministic conflict map routes disagreements or structural contradictions to targeted pairwise resolution. The arbiter then outputs the final task label from raw target text, compact analyst reports, and any targeted resolutions. Detection may end with no accepted fallacy and map to `Non-Fallacious`. Classification is forced-choice: if viability pruning leaves no survivor, an explicit recovery adjudicator chooses from pre-pruning proposals or, when all experts abstain, from the full eight-label space. Recovery is recorded in the trace. There is no generic debate, hidden planner, voting protocol, or decomposer.

## Metrics

Detection reports accuracy, positive-class precision/recall/F1, false positive rate, false negative rate, and a confusion matrix. Classification reports accuracy, macro-F1 over all eight CoCoLoFa labels, per-label scores, and an 8x8 confusion matrix.

## Tests

```powershell
pytest -q
```
