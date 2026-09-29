# Semantic Detopicalization and Definition Induction Design

## Goal

Replace the experimental property-graph path with a reproducible, staged
pipeline that induces fallacy definitions from positive training examples by
preserving inferential structure while removing topic-specific content.

## Scope and cleanup

The property-graph experiment is obsolete for this workflow. The change removes
its source package, tests, configuration, documentation, package entry point,
and generated `runs/property-graph-*` outputs. It does not remove unrelated
classification, detection, adjudication, or evidence code.

CMPV run summaries remain available. To reduce workspace noise, only YAML trace
files under directories whose names contain `cmpv` are removed; each run keeps
its manifest, metrics, predictions, and API audit files.

## Architecture

The new implementation lives under `src/induction/`. It reuses the existing
dataset loader and structured LLM client, but keeps all induction-specific
schemas, prompts, checkpoints, audits, embeddings, clustering, and reports in
its own package. The `scripts/` modules are thin command-line entry points for
individual stages and a hard-gated full pipeline.

The data flow is:

```text
train split
  -> positive sample selection and data_stats.json
  -> semantic extraction with checkpoint/resume
  -> semantic audit and collapse check
  -> normalized sentence embeddings of canonical_reasoning only
  -> cosine k-medoids search and candidate metrics
  -> member-level cluster audit
  -> cluster mode induction
  -> conservative mode merge
  -> induced definition and provenance manifest
```

Each stage reads the previous stage's artifacts and refuses to continue when a
required gate has not passed. The `none` label is rejected for this positive
induction phase; boundary induction is a separate future experiment.

## Components

- `src/induction/config.py`: YAML configuration and environment-variable
  mapping, including the data path, selected label, model settings, stage
  options, and output directory.
- `src/induction/data.py`: validated positive-sample loading, duplicate checks,
  stable JSONL serialization, and data statistics.
- `src/induction/contracts.py`: semantic, cluster-audit, mode, merge, and final
  definition schemas plus validation helpers. Semantic records must be
  produced by the LLM; local code may reject or retry invalid records but may
  not invent semantic content.
- `src/induction/prompts.py`: prompt text for semantic extraction, cluster
  audits, mode induction, merging, and final definition induction. Prompts do
  not expose predefined reasoning modes.
- `src/induction/llm.py`: adapter over the existing client with stage metadata,
  strict JSON schemas, progress checkpointing, and resumable keyed records.
- `src/induction/embedding.py`: lazy Hugging Face model loading, device
  selection, normalized embeddings, and embedding manifest generation. It
  fails loudly if the requested model cannot be loaded and never falls back to
  TF-IDF.
- `src/induction/clustering.py`: cosine distance, deterministic seeded
  k-medoids with multiple restarts, medoid selection, k-search metrics, and
  diagnostic purity calculations. A declared agglomerative fallback is used
  only when the primary implementation cannot run and is recorded in output.
- `src/induction/audit.py`: semantic audit reports, representation-collapse
  checks, member selection, cluster audit preparation, and cluster gate checks.
- `src/induction/reporting.py`: JSONL/CSV/Markdown artifacts and the complete
  reproducibility manifest with prompt hashes and no secrets.
- `src/induction/pipeline.py`: stage orchestration and hard gates used by the
  eight CLI modules.

## Contracts and gates

Semantic extraction returns, at minimum, premises, conclusion, bridge,
inference source/target, evidential basis, polarity, conclusion direction,
canonical reasoning, and audit notes. Nullable fields remain nullable when a
field is not applicable. `canonical_reasoning` must be grammatical prose, not
tags, and must preserve opposite conclusion directions.

The semantic gate fails when samples are missing, records are invalid, known
hard cases are not present in the audit report, canonical representations
collapse severely, or topic leakage/copying checks fail. Embedding is forbidden
until this gate passes.

The cluster gate records silhouette and size diagnostics but does not treat
silhouette as sufficient. It blocks mode and definition induction when the
member audit reports heavy opposite-direction mixing, heterogeneous giant
clusters, or mostly non-representative medoids.

## Configuration and outputs

`configs/induction.yaml` defaults to `data/cocolofa/train.json`, the
`appeal to tradition` label, seed `42`,
`sentence-transformers/all-mpnet-base-v2`, normalized vectors, k range `6..25`,
and `outputs/appeal_to_tradition_induction`. Environment variables for the LLM
API key, base URL, and model are read through the config and are never written
to logs or manifests.

The full run writes the specified data stats, positive samples, semantic
records/failures, audit reports, embeddings and manifest, k metrics, cluster
assignments/member audit, cluster modes, merge plan, induced definition, and
run manifest. Every induced mode cites cluster IDs and supporting sample IDs.

## Testing strategy

Tests are organized by stage. Pure data, schema, embedding-input, clustering,
audit, manifest, and gate behavior use deterministic fixtures. LLM stages use
the existing mock transport and assert that invalid or missing records stop the
pipeline and that resume skips completed sample keys. CLI smoke tests run a
small local fixture without downloading a model or calling an external API.

The final experiment is not fabricated by tests: a real run requires the
configured LLM credentials and Hugging Face model availability. If either is
unavailable, the command reports the blocking error and preserves completed
checkpoints.
