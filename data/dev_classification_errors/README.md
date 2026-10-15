# Classification error development set

66 samples misclassified by the single-LLM zero-shot classification baseline, selected from 481 CoCoLoFa test classification samples.

Source run: `runs/classification-test-single-llm` (2026-09-20), context: `paper`.
Selection: `status == "ok"` and `prediction != gold`.

`dev.json` contains the original sample ID, article ID, title, target comment, parent comment, gold label, and baseline prediction. Text and gold labels are preserved from `data/cocolofa/test.json`. It is compatible with `src.discourse_classification.data.load_records`; `baseline_prediction` is inspection metadata and is not included in model inputs by that loader.

This is a diagnostic development set derived from the original test split. Samples used for development are exposed and must not be reported as fresh held-out test evaluation. The original splits remain unchanged.
