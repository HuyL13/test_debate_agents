# CoCoLoFa full-test comparison

Updated UTC: 2026-09-07T05:11:06.514696+00:00

Published baselines: [CoCoLoFa paper, Tables 4 and 5](https://aclanthology.org/2024.emnlp-main.39.pdf). These are published numbers, not baseline reruns. All scores below are percentages.

| Method | Detection P | Detection R | Detection F1 | Classification P | Classification R | Classification macro-F1 |
|---|---:|---:|---:|---:|---:|---:|
| BERT / trained on Reddit (paper) | 62 | 89 | 73 | 65 | 64 | 62 |
| BERT / trained on CoCoLoFa (paper) | 83 | 89 | 86 | 85 | 86 | 86 |
| NLI / trained on Reddit (paper) | 62 | 96 | 75 | 70 | 67 | 66 |
| NLI / trained on CoCoLoFa (paper) | 82 | 86 | 84 | 87 | 87 | 87 |
| GPT-4o / zero-shot (paper) | 72 | 88 | 79 | 82 | 80 | 79 |
| GPT-4o / few-shot (paper) | 72 | 79 | 75 | 84 | 84 | 83 |
| GPT-4o / CoT (paper) | 76 | 82 | 79 | 85 | 85 | 85 |
| Llama3 8B / zero-shot (paper) | 76 | 43 | 55 | 57 | 42 | 41 |
| Llama3 8B / few-shot (paper) | 62 | 95 | 75 | 57 | 50 | 48 |
| Llama3 8B / CoT (paper) | 77 | 56 | 65 | 63 | 58 | 58 |
| gpt-oss-20b / single (this repo) | pending | pending | pending | pending | pending | pending |
| gpt-oss-20b / adaptive (this repo) | pending | pending | pending | pending | pending | pending |

## Run status

| Run | Completed / required | State | Launches |
|---|---:|---|---:|
| detection / single | 3 / 798 | running | 1 |
| detection / adaptive | 0 / 798 | running | 1 |
| classification / single | 1 / 481 | running | 1 |
| classification / adaptive | 0 / 481 | running | 1 |

## Evaluation conditions

- Full original test split: detection 798 comments; classification 481 gold-positive comments, independently selected.
- Frozen source, prompts, data hashes and configs; no prompt or model selection from test outcomes.
- NVIDIA openai/gpt-oss-20b, temperature 1, max output 4096; title + immediate same-article parent + target.
- Single and PARD-inspired adaptive are new methods, not reproductions of the paper models. Adaptive budget is at most 3 rounds.
- Detection uses positive-class P/R/F1. Classification uses unweighted macro P/R/F1 across all eight labels; paper explicitly specifies macro-F1, but its exact P/R averaging implementation is unavailable.
- Different models, prompting and training regimes: this table is descriptive, not a controlled claim of architectural superiority. One stochastic run per method; no significance claim.
- One broken test parent reference is left empty and the comment is retained, as documented in UPSTREAM_AUDIT.md.
- Pending or failed runs have no score. Final scores require full ID coverage and manifest validation.
- The computer must remain awake with network access. Raw logs and per-sample checkpoints are in outputs/full-test-v1/.
