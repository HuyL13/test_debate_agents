# Diagnostic Debate V1

Diagnostic Debate V1 separates diagnosis from task-label prediction.

Flow:

```text
Input + context
-> ArgumentDecomposer
-> Inference / Evidence / SemanticContext diagnoses
-> optional role-preserving review
-> DiagnosticArbiter
-> task label
```

Policies:

- `diagnostic_no_debate`: one decomposition, three independent diagnoses, one arbiter.
- `diagnostic_review`: one decomposition, three independent diagnoses, one isolated review per diagnostic role, one arbiter.

The legacy PARD-inspired planner and debate protocols remain available through
the existing `single`, `no_deliberation`, `fixed`, `adaptive_policy: planner`,
and `adaptive_policy: disagreement` modes. Their protocol executors now live
under `src/legacy_protocols`.

Only `DiagnosticArbiter` receives the task label space. The decomposer,
diagnostic specialists and diagnostic reviewers use schemas without
`prediction`.
