# CoCoLoFa Property-Graph Induction Design

## Goal

Build a definition-initialized, train-refined property graph for the eight-way
CoCoLoFa fallacy-classification task. The implementation must reuse the
repository's dataset loader, LLM client, response cache, audit logging, and
current `.env`-driven NVIDIA configuration. Initial verification uses only a
small train smoke set; a full 3,168-sample extraction is outside this change.

## Scope

The first version implements:

- positive classification-train preparation;
- one structured LLM extraction per selected sample;
- deterministic signature normalization;
- definition-based seed-graph construction;
- within-label prototype induction;
- cross-label shared-mechanism and discriminative-condition induction;
- graph validation, versioned JSON persistence, and inverted indexes;
- deterministic graph retrieval and retrieval metrics;
- an audit report and a seed-versus-evolved graph-change report;
- a CLI capable of running each stage or the smoke pipeline.

The first version does not implement GNNs, Neo4j, multi-agent extraction,
embedding-based topic features, online mutation, automatic prototype naming,
or a new final-label LLM classifier. Retrieval returns ranked label evidence
for a later classifier. Test data is never used for induction or tuning.

## Repository Integration

The feature lives under `src/property_graph/` rather than altering the existing
adjudication engine:

- `schemas.py`: controlled vocabularies, JSON schemas, and semantic validators.
- `extraction.py`: leakage-safe prompts and one-call signature extraction.
- `normalization.py`: deterministic structural feature generation.
- `seed.py`: immutable label definitions and seed-graph construction.
- `graph_io.py`: validation, serialization, adjacency, and subgraph helpers.
- `induction.py`: similarity, clustering, prototypes, shared mechanisms, and
  discriminative conditions.
- `indexing.py`: feature, label, and mechanism indexes.
- `retrieval.py`: prototype scoring, label aggregation, and neighborhood output.
- `reporting.py`: induction audit, graph diff, and retrieval metrics.
- `pipeline.py`: stage orchestration, resume behavior, versioning, and CLI.

Configuration is stored in `configs/property_graph.yaml`; label definitions are
stored in `definitions/fallacy_labels.json`. Runtime artifacts live below an
output directory supplied to the CLI, defaulting to `runs/property-graph/`, so
smoke artifacts do not become source files accidentally.

## Model Configuration and Call Contract

The pipeline loads `.env` with the existing configuration utilities. The model
uses `NVIDIA_API_KEY`, `NVIDIA_BASE_URL`, and `NVIDIA_MODEL` through the existing
`ModelConfig` and `Client`; credentials are never copied into configs, logs, or
reports.

Each selected sample causes exactly one logical `Client.generate` call. Provider
retries required to obtain valid schema output remain the responsibility of the
existing client and are recorded separately. The extraction cache key already
includes model configuration, request metadata, prompt, and schema. Metadata
also includes the sample ID, split, stage, prompt version, and signature schema
version.

The model-visible payload contains only title, parent comment, and target
comment. Gold labels, candidate labels, label definitions, and fallacy names do
not appear in either extraction prompt. The gold label is attached to the
validated signature record only after `generate` returns. Tests inspect the
actual prompt and metadata boundary to enforce this property.

Invalid output is retried by the existing client. A terminal extraction failure
is appended to `extraction_failures.jsonl`, the remaining smoke samples continue,
and no synthetic signature is created.

## Signature and Normalization

The signature schema uses fixed proposition roles, speaker roles, relation
types, semantic-role values, qualifier fields, evidence spans, and uncertainty
entries from the guide. Semantic validation additionally requires unique
proposition IDs, valid relation endpoints, and evidence spans drawn from the
provided text.

Normalization emits only structural features, including relation type,
source/target proposition roles, controlled semantic roles, scope transitions,
qualifiers, and controlled structural flags. It never emits raw entities,
free-form proposition text, or topical tokens. Records persist raw extraction,
normalized signature, sorted feature set, gold label, split, and sample ID.

## Seed Graph

The seed graph contains eight locked label nodes, definition-derived abstract
mechanisms, and definition-derived conditions. Official dataset label names and
repository label IDs are authoritative. Definitions are immutable metadata;
induction may add nodes and edges or update support/weights but may not remove
or rewrite label definitions.

Every build records schema version, graph version, dataset/task, selected train
sample count, timestamp, Git commit, configuration hash, extraction prompt
version, and train-selection hash.

## Deterministic Induction

Structural similarity is a weighted Jaccard combination of relation, semantic,
and qualifier/scope feature families, initially weighted `0.50`, `0.35`, and
`0.15`. To avoid a new numerical dependency, v1 uses deterministic
threshold-connected components as the agglomerative equivalent: samples within
each label are connected when distance is at most the configured threshold;
connected components smaller than `min_cluster_size` enter the outlier pool.

Each retained cluster creates one prototype. Features present in at least the
required ratio are required; features above the typical ratio are typical; the
rest are variants. Up to three medoid samples are selected deterministically by
average structural distance and stable sample-ID tie-breaking. Prototype names
are deterministic IDs/descriptions, not extra LLM calls.

Cross-label induction compares prototype required-feature cores. Qualifying
overlap creates a shared-mechanism node and edges to participating labels.
Smoothed log odds over label feature frequencies creates discriminative
condition nodes and `DIFFERS_BY` edges. Every induced node and edge includes
support counts, sample provenance, participating labels, and relevant induction
thresholds. Induction uses no raw lexical content.

The small smoke set may not contain enough support for all eight labels or a
shared mechanism. Smoke-specific thresholds may be lower than production
defaults, and the report must identify which production success criteria remain
unproven rather than fabricate structures.

## Graph Persistence and Evolution

JSON is the source of truth. Validation requires unique node and edge IDs,
existing edge endpoints, locked label nodes, allowed node/edge types, finite
weights, non-negative support counts, and provenance on all induced structures.
Serialization is deterministic and round-trips without information loss.

Each build writes a new version under `graph_versions/` and updates a separate
current graph file only after validation succeeds. Supported evolution effects
are `ADD_PROTOTYPE`, `ADD_SHARED_MECHANISM`,
`ADD_DISCRIMINATIVE_CONDITION`, and `UPDATE_EDGE_WEIGHT`; seed definitions are
never overwritten.

## Indexing and Retrieval

Indexing produces feature-to-prototypes, label-to-nodes, and
mechanism-to-examples JSON files. Retrieval needs no LLM once given a signature:
it normalizes features, generates candidates through the feature index, scores
prototypes using required coverage, Jaccard overlap, typical coverage, and a
discriminative bonus, then aggregates each label by its maximum prototype
score.

Results include ranked labels, matched prototypes, shared mechanisms, matched
conditions, missing required conditions, contradictions when represented,
`DIFFERS_BY` evidence, and representative sample IDs. Dev evaluation reports
Recall@1 through Recall@4 and MRR. Smoke verification may exercise retrieval on
held-out train samples, clearly labeled as a functional check rather than a dev
metric or research result.

## Seed-to-Evolved Change Inspection

Every induction run writes both machine-readable `graph_diff.json` and readable
`graph_diff.md`. Comparison is by stable node/edge ID and reports:

- seed and evolved node/edge totals, grouped by type;
- added, removed, and modified nodes and edges;
- edge-weight and support-count deltas;
- induced prototypes per label and their required/typical features;
- shared mechanisms and participating labels;
- discriminative conditions and contrast labels;
- provenance sample IDs for every addition or modification;
- outlier counts and ratios by label;
- unchanged locked seed nodes and any invariant violation.

For the smoke run, the final handoff summarizes these changes and links the seed
graph, evolved graph, and diff report. A zero-change result is treated as a
diagnostic outcome and explained from thresholds/sample coverage, not presented
as successful induction.

## CLI and Smoke Run

The primary CLI supports independent `prepare`, `extract`, `seed`, `induce`,
`index`, `retrieve`, `evaluate`, and `smoke` commands. `smoke` selects a stable,
label-stratified subset of train examples, with an explicit limit. It never
falls back to dev or test to fill missing labels. Extraction supports resume and
does not repeat cached completed samples.

The initial live smoke target is 8–16 train samples, chosen to cover as many of
the eight labels as possible. Before any live request, unit tests run against
the mock transport. The live run uses the current `.env` and records provider
calls, cache hits, retries, token usage, and failures without exposing secrets.

## Testing and Acceptance

Implementation follows test-driven development. Tests cover:

- schema acceptance/rejection and referential integrity;
- prompt/metadata leakage prevention and one logical call per sample;
- deterministic normalization without lexical features;
- seed locking and graph round-trip behavior;
- similarity, clustering, medoids, prototypes, outliers, shared mechanisms,
  discriminative conditions, and provenance;
- indexing and retrieval scoring;
- graph-diff detection for additions and weight/support changes;
- pipeline resume/failure behavior and train-only selection.

Acceptance requires the full local test suite to pass, a live train-only smoke
run to complete or report provider failures honestly, and generation of a valid
seed graph, evolved graph, indexes, audit report, and seed-to-evolved diff. No
claim about all eight labels, dev Recall@4, or full-dataset quality is made from
the smoke subset.
