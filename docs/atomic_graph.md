# Atomic graph smoke test

## Semantic repair v3

```powershell
.\.venv\Scripts\python.exe -m src.atomic_graph --config configs/atomic_graph_v3.yaml --limit 10 --seed 42 --output outputs/atomic_graph_v3_seed42
```

V3 segments source sentences deterministically, extracts nodes first, verifies/repairs their semantics, locks node IDs and then extracts/verifies relations. The enabled semantic reviewer adds two calls per accepted sample beyond the two extraction calls; retries are bounded by `max_semantic_repairs` and provider retry settings. Remaining issues block final graph output and are preserved in trace and QA files. Set `semantic_review: false` only for explicitly structural experiments; the report records that distinction.

The final schema uses `speech_act` plus multiple scope operators, entity/proposition references and sentence-relative character spans. Provider quotes are exact substrings with 1-based occurrence; Python computes zero-based, end-exclusive Unicode character offsets. Repeated quotes must identify occurrence. The original connective whitelist remains closed, including omission of `so` and `once`; surface markers can record those words and SUPPORT remains independent.

For relations, Python derives complete evidence spans from the verified locked endpoint nodes and exact marker quotes. The model can supply additional contextual evidence quotes. This avoids having the model recopy fixed source spans; full-source semantic review still checks whether that provenance actually justifies the relation.

Structural checks verify provenance, IDs, paired conditional groups, endpoint evidence, explicit connective spans and SUPPORT DAG. Conservative cue checks catch missing question, leading-if, hedge and should scopes and some predicate fragments. These are guardrails, not a grammar parser or proof of semantic fidelity. The source-grounded semantic reviewer checks omissions, over-splitting, attribution and relation function. Its acceptance is a reviewer judgment, not gold correctness.

Outputs require a fresh directory and preserve v2. They include `traces`, `semantic_review.jsonl`, `prompt_version.txt`, `config_snapshot.json` and `report.json`, in addition to inputs/accepted graphs/linearizations. Failed drafts exist only in trace, never as final graphs. Reports distinguish accepted samples from failures and include counts, operator distribution, issues, tokens and latency; no accuracy is claimed.

For smoke/manual review, `src.atomic_v3_runner.apply_manual_review(output, issues)` verifies original quotes and records PASS/NEEDS_HUMAN_REVIEW. A concrete remaining semantic defect overrides automatic acceptance: the graph and canonical text move to `drafts`, and final report counts exclude them. Draft content is preserved unchanged. `automatic_valid` preserves the earlier machine acceptance count. `manual_review.json` and the semantic log contain the review reasons.

The seed-42 ten are a development/regression set already used to design this repair. Use another seed after freezing schema/prompts for exploratory hold-out review; do not use labels or sample IDs in model-visible prompts. Dataset IDs are stored only in app metadata/artifacts. Baseline results are not overwritten.

Standalone validation accepts a graph and a UTF-8 file containing its original comment:

```powershell
.\.venv\Scripts\python.exe -m src.atomic_resources.validate_atomic_graph_v3 graph.json original.txt
```

## Baseline v2

Run from the repository root with the existing NVIDIA environment variables in `.env`:

```powershell
.\.venv\Scripts\python.exe -m src.atomic_graph --limit 10 --seed 42
```

This selects ten complete comments from the Cocolofa test split, without filtering by gold label. The seed makes selection reproducible. No gold labels, article text or parent comments are sent to the extractor. To try another selection, change `--seed` and use a new `--output` directory. Existing output directories accept only the same input selection, preventing mixed runs.

Configuration: `configs/atomic_graph.yaml`. The default uses JSON object output for compatibility with the supplied schema's conditional connective constraints. Local JSON Schema and graph validation remain strict; set `structured_output: true` only with a provider supporting this schema.

The smoke-test configuration uses `reasoning_effort: low` and an 8192-token completion budget for the configured GPT-OSS model. Remove the reasoning setting for providers that do not support it.

Output in `outputs/atomic_graph_10`:

- `inputs.json`: selected IDs and original comments.
- `graphs/*.json`: only validated v2 graph objects.
- `linearized/*.txt`: node text and modes, SUPPORT groups, discourse edges and deterministic order.
- `report.json`: validation outcomes and graph counts per sample.
- `api_calls.jsonl`, `raw_calls.jsonl`: audit and full model responses for inspection.
- `cache.sqlite3`: reusable validated responses for reruns.

The supplied schema and validator are preserved in `src/atomic_resources`. Additional checks require consecutive sentence IDs, complete verbatim source coverage, matching document ID and whole-phrase explicit connectives. SUPPORT topological order uses sentence order then proposition ID, retaining disconnected nodes and joint support. Discourse edges do not impose SUPPORT dependencies.

Validation failures trigger the existing client's bounded retries. Failed samples are recorded and do not receive a canonical graph; the command exits with status 1 if any fail. Cache reuse requires matching input, model, schema and prompt.

Review each graph against its original comment. Structural validation cannot establish atomicity, scope preservation, the rhetorical use of a connective, or semantic correctness of inferred relations and SUPPORT. No classification or performance comparison is performed.
