# Atomic graph smoke test

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
