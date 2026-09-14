# Dataset

CoCoLoFa is sourced from `https://github.com/Crowd-AI-Lab/cocolofa` at commit `c39d45fdd57401e1f6cb674f25113dfa0304e734`.

At that commit, upstream provides:

- `train.json`
- `dev.json`
- `test.json`

This repository tracks `data/cocolofa/provenance.json`. The split JSON files are prepared locally by `scripts/prepare_data.py` and ignored by Git.

Detection uses every eligible comment and predicts `Fallacious` or `Non-Fallacious`. Classification filters to gold-positive comments and predicts one of the eight CoCoLoFa fallacy labels.
