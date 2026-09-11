# Simplified A/B flows

The supplied plan skips some middle sections. This implements its available rules
and checklist using a minimal extractive decomposer.

- A: three independent analysts -> optional existing debate -> arbiter.
- B: extractive decomposer -> the same analysts -> optional existing debate -> arbiter.
- Agent and arbiter JSON contains only `prediction` and `content`.
- Classification has exactly eight labels; detection has exactly two.
- Decomposition contains only `premises` and `conclusion`, verbatim target spans.
  Empty values mean no explicit span. Code rejects non-verbatim spans; prompts
  prohibit hidden premises. Substring validation cannot prove semantic completeness
  or that a span actually functions as a premise. Review these aspects in traces.
- Shared structural rules cover all eight labels, including longevity as a reason
  to preserve a practice versus longevity describing an entrenched problem.

Existing planner and protocol execution is reused. Internal IDs are retained for
compatibility, with `agent_roles` in traces documenting their new meaning:
`Factual` = Argument-Scheme Analyst, `Logical` = Enthymeme & Commitment Analyst,
`Contextual` = Critical Evaluation Analyst. A/B use identical role prompts.
Legacy configurations retain their previous behavior (`flow: null`). Categorical
reports support early stopping without invented confidence. Paired configs disable
early stopping and use the same two-round planner budget.

## Paired dev experiments

With `NVIDIA_API_KEY` available in the process environment:

```powershell
.\.venv\Scripts\python.exe -m src.run_two_flows --task detection --output outputs/nvidia-two-flow-detection-dev16
.\.venv\Scripts\python.exe -m src.run_two_flows --task classification --output outputs/nvidia-two-flow-classification-dev16
```

Each command runs A1 and B1 before A2 and B2 on `data/diagnostic_dev16`, using the
same model, temperature, context and budget. Classification uses gold-positive
samples only. This small dev comparison is not a representative final evaluation.
`--limit` selects the same prefix for all variants; `--resume` resumes failed runs.
Existing runner manifests require unchanged model/source/config when resuming.

Each run preserves raw calls, sample traces, predictions and metrics. The root
`comparison.json` contains summaries and per-sample fixed/regressed transitions.
Inspect raw text and traces for HG without samples, FD without exhaustiveness,
SS without progression, Majority/HG and Worse Problems/Tradition confusions.
These semantic errors are not measured automatically by keyword matching.

Prefer A when dev results are comparable; freeze before final test evaluation.
Roles operationalize scheme analysis, conservative reconstruction and evaluation
of premise-conclusion support. No claim is made that prior research proposed this
exact three-agent architecture.
