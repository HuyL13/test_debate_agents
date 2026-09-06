# CoCoLoFa PARD adaptation

Authorized scope: implement the supplied baseline guide in a new local Git repository.

## Architecture
Python 3.11 package, immutable text-only model input separated from labeled samples,
strict upstream JSON loader, independent detection and gold-positive classification.
Default context is target comment + news title + immediate parent comment (Appendix C).
Full article context is an explicitly named, non-comparable ablation.

Independent role reports precede the API strategy planner, matching PARD phase 1/2.
The planner returns a validated protocol, topic, role order, teams, examiner and budget.
Three protocol implementations preserve sequential exchange, 2v1 debate, and one
examiner/two respondents with reflection. Final arbiter performs verdict synthesis.
No retrieval, model selection, RL, feedback memory, or new proposed architecture.

## Reliability and reproducibility
OpenAI-compatible Chat Completions transport with strict JSON Schema, finite retry
budgets, HTTP timeout/backoff, raw attempt logs and SQLite cache keyed by request
and dataset/task/sample/role/protocol identity. Cache hits incur zero new usage.
Every run records a source/config/dataset fingerprint and selection manifest.
Resume rejects incompatible manifests. Failed samples remain explicit; incomplete
runs cannot silently produce benchmark scores. Test runs require a frozen manifest.

## Validation
Unit tests cover schema/filtering, missing parents, label leakage, independent
hand-calculated metrics, role participation and turn ordering, early stopping,
invalid API output, retry accounting, cache isolation and CLI/resume/freeze.
Offline smoke runs use 10 dev samples per task and exercise all ablations; synthetic
scores are never presented as real benchmark performance. Real API execution
requires a user-provided environment key and explicitly configured model.

## Decisions
Reimplement a compact engine instead of importing upstream scripts: those scripts
include broken imports/parser paths and fake-news-specific RL/retrieval dependencies.
Keep upstream clones and immutable commit references for inspection. Do not copy
unlicensed upstream code or bundle upstream datasets into Git history.
