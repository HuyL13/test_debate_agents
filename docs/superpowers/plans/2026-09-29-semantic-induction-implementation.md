# Semantic Induction Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (or subagent-driven-development). Steps use checkbox syntax for tracking.

**Goal:** Remove the obsolete property-graph experiment and implement the staged semantic-detopicalization, sentence-embedding, clustering, audit, and definition-induction pipeline from the approved design.

**Architecture:** Add an isolated src/induction/ package that reuses src.data.loader, src.llm.Client, and src.io_utils. Stage scripts call package functions, persist the specified artifacts, and enforce semantic/cluster gates. Use seeded NumPy k-medoids with a recorded agglomerative fallback; never silently fall back to TF-IDF.

**Tech Stack:** Python 3.11, PyYAML, jsonschema, python-dotenv, NumPy, scikit-learn, sentence-transformers, pandas, tqdm, pytest.

**Spec:** docs/superpowers/specs/2026-09-29-semantic-induction-design.md

## Global Constraints

- Read real positive samples from data/cocolofa/train.json; never hard-code counts, IDs, clusters, silhouette values, or induced modes.
- Semantic and induction text must come from the configured LLM. Local code may validate, retry, checkpoint, and report but may not fabricate semantic content.
- Embed only canonical_reasoning; do not concatenate original text, article/title/parent context, definitions, or mode names.
- Main model is sentence-transformers/all-mpnet-base-v2 with normalized vectors and no silent TF-IDF fallback.
- Reject none for this positive-induction phase.
- A failed semantic gate blocks embedding; a failed cluster gate blocks mode/definition induction.
- Never write API keys to output, logs, manifests, or tests.
- Keep CMPV summaries, delete only CMPV trace YAML, and remove the obsolete property-graph code/config/docs/runs.

---

### Task 1: Configuration, data artifacts, and contracts

**Files:**
- Create: src/induction/__init__.py
- Create: src/induction/config.py
- Create: src/induction/contracts.py
- Create: src/induction/data.py
- Create: configs/induction.yaml
- Create: tests/induction/test_config_data_contracts.py

**Interfaces:**
- load_config(path) -> InductionConfig
- load_positive_samples(config) -> (list[dict], dict)
- semantic_schema(), cluster_audit_schema(), cluster_mode_schema(), merge_plan_schema()
- validate_semantic_record(record, sample) -> dict

- [ ] Write tests for relative config paths, default values, none-label rejection, positive selection, duplicate statistics, and invalid canonical_reasoning.
- [ ] Run:
  
  ~~~text
  .\.venv\Scripts\python.exe -m pytest tests/induction/test_config_data_contracts.py -q
  ~~~
  
  Expected: collection fails because src.induction does not exist.
- [ ] Implement typed YAML config loading with defaults: train data, Appeal to Tradition, seed 42, all-mpnet-base-v2, k 6..25, output outputs/appeal_to_tradition_induction. Resolve relative paths from the config file.
- [ ] Reuse src.data.loader.load_split, select only the configured positive label, serialize sample_id/article_id/comment_id/title/comment/parent_comment/article/fallacy, and compute counts/duplicate IDs/normalized-comment duplicates from actual data.
- [ ] Implement strict JSON-schema-like contracts. Require premises, conclusion, bridge, inference source/target, polarity, conclusion direction, canonical reasoning, and allow null only for non-applicable fields.
- [ ] Run the focused tests and expect all pass.
- [ ] Commit with message feat: add semantic induction contracts.

### Task 2: Semantic prompts, LLM extraction, and resume

**Files:**
- Create: src/induction/prompts.py
- Create: src/induction/semantic.py
- Create: scripts/semantic_extract.py
- Create: tests/induction/test_semantic_extraction.py
- Modify: src/llm/mock.py

**Interfaces:**
- semantic_extraction_prompt(sample, use_parent_context=False) -> (system, user)
- extract_semantic_records(config, samples, client, resume=False) -> list[dict]
- semantic_prompt_hash() -> str

- [ ] Write tests proving the prompt contains the real target comment, says not to classify into predefined subtypes, preserves opposite directions, and uses no gold definition.
- [ ] Write a resume test that pre-populates semantic_records.jsonl and verifies the keyed sample is not sent again.
- [ ] Write a failure test proving an unavailable LLM creates semantic_failures.jsonl and raises instead of creating a placeholder.
- [ ] Run the focused tests and expect missing-module failure.
- [ ] Implement the six-step prompt order: premise, conclusion, bridge, direction/polarity, detopicalization, grammatical canonical reasoning. Use strict schema metadata stage semantic_extraction and validate every response.
- [ ] Append each successful record immediately, use (article_id, comment_id) as the resume key, recover torn JSONL tails, and never log secrets. Add deterministic schema-valid semantic_extraction output to MockTransport.
- [ ] Run focused tests and expect all pass.
- [ ] Commit with message feat: add checkpointed semantic extraction.

### Task 3: Semantic audit and sentence embeddings

**Files:**
- Create: src/induction/audit.py
- Create: src/induction/embedding.py
- Create: scripts/audit_semantics.py
- Create: scripts/embed_reasoning.py
- Create: tests/induction/test_semantic_audit_embedding.py
- Modify: requirements.txt
- Modify: pyproject.toml

**Interfaces:**
- audit_semantics(config) -> dict
- check_representation_collapse(records, embeddings=None) -> dict
- embed_reasoning(config) -> dict
- embed_records(records, config, model=None) -> dict

- [ ] Write tests for incomplete-record blocking, exact/near collapse metrics, original-copy/topic-leakage checks, canonical-only model input, normalized output, and refusal when semantic_gate.json says passed=false.
- [ ] Run the focused tests and expect missing-module failure.
- [ ] Implement fixed-seed random audit, required Appeal-to-Tradition hard-case reporting when IDs exist, exact duplicate counts, near-collapse checks, and semantic_audit.md plus representation_stats.json.
- [ ] Make embedding imports lazy. Load SentenceTransformer only in the stage, choose CUDA if available, encode only canonical_reasoning, normalize the final vectors, save canonical_embeddings.npy and embedding_manifest.json, and fail loudly on model load/download failure.
- [ ] Add runtime dependencies numpy, scikit-learn, sentence-transformers, pandas, and tqdm without pinning or reinstalling torch. Run focused tests without downloading a model.
- [ ] Commit with message feat: add semantic audit and sentence embeddings.

### Task 4: Cosine k-medoids and k search

**Files:**
- Create: src/induction/clustering.py
- Create: scripts/cluster_search.py
- Create: tests/induction/test_clustering.py

**Interfaces:**
- cosine_distance_matrix(embeddings) -> ndarray
- fit_kmedoids(distance_matrix, k, seed, restarts) -> dict
- choose_medoid(indices, distance_matrix) -> int
- search_k(config, embeddings, records) -> dict
- select_member_audit_rows(assignments, records, distances, nearest_n, farthest_n) -> list[dict]
- majority_purity(cluster_ids, values) -> float

- [ ] Write tests proving medoids are actual members, same seed is reproducible, purity is diagnostic only, and each cluster yields medoid/nearest/boundary member rows.
- [ ] Run focused tests and expect missing-module failure.
- [ ] Implement cosine distances, seeded multi-restart k-medoids, deterministic tie-breaking, silhouette/size/tiny/giant/intra-cluster metrics, and actual relation-polarity/conclusion-direction/premise-valence purity diagnostics.
- [ ] Select roughly three candidates using multiple signals rather than argmax silhouette. Write k_search_metrics.csv, cluster_assignments.jsonl, and cluster_search.json with the actual method and seed.
- [ ] Record agglomerative fallback only when primary clustering cannot run; never substitute TF-IDF.
- [ ] Run focused tests and commit with message feat: add cosine k-medoids search.

### Task 5: Cluster audit, mode induction, merge, and final definition

**Files:**
- Modify: src/induction/prompts.py
- Modify: src/induction/contracts.py
- Create: src/induction/induction.py
- Create: scripts/audit_clusters.py
- Create: scripts/induce_cluster_modes.py
- Create: scripts/induce_definition.py
- Create: tests/induction/test_cluster_induction.py

**Interfaces:**
- audit_clusters(config) -> dict
- induce_cluster_modes(config) -> list[dict]
- merge_cluster_modes(config, modes) -> dict
- render_induced_definition(label, modes, provenance) -> str
- induce_definition(config) -> dict

- [ ] Write tests for strict cluster-audit fields, failed cluster-gate blocking, conservative KEEP SEPARATE behavior, and final output citing cluster IDs and supporting sample IDs.
- [ ] Run focused tests and expect missing-module failure.
- [ ] Implement cluster prompts containing only cluster ID/size, medoid original/canonical text, nearest/boundary members, and audit context; do not provide predefined mode names.
- [ ] Write cluster_member_audit.md and cluster_audits.jsonl. Block mode induction when opposite-direction mixing, giant heterogeneous clusters, or non-representative medoids breach the gate.
- [ ] Implement mode induction with premise/conclusion/bridge, non-invariants, boundaries, supporting member IDs, and coverage. Implement conservative merge from summaries; preserve modes whenever direction/evidence/bridge differs.
- [ ] Implement final Markdown with core invariant, prototypical relation, discovered modes, boundaries, dataset-edge modes, operational test, and provenance. Include INDUCTION READY/PARTIALLY READY/NOT READY based on audit evidence.
- [ ] Run focused tests and commit with message feat: induce audited reasoning modes and definitions.

### Task 6: Reporting, CLI stage wrappers, hard-gated orchestration, and docs

**Files:**
- Create: src/induction/reporting.py
- Create: src/induction/pipeline.py
- Modify: scripts/audit_semantics.py
- Modify: scripts/embed_reasoning.py
- Modify: scripts/cluster_search.py
- Modify: scripts/audit_clusters.py
- Modify: scripts/induce_cluster_modes.py
- Modify: scripts/induce_definition.py
- Create: scripts/run_induction.py
- Create: tests/induction/test_pipeline.py
- Modify: README.md

**Interfaces:**
- run_induction(config_path, resume=False) -> Path
- write_run_manifest(output_dir, manifest_data) -> Path
- Each script supports --config; semantic_extract and induce_cluster_modes support --resume.

- [ ] Write tests proving stage order, stop-on-semantic-gate failure before embedding, stop-on-cluster-gate failure before mode induction, CLI module importability, and absence of API keys from run_manifest.json.
- [ ] Run focused tests and expect missing pipeline failure.
- [ ] Implement ordered stages: data -> extraction -> semantic audit -> collapse gate -> embedding -> k search -> cluster audit -> mode induction -> merge -> definition. Preserve completed checkpoints on failure and return non-zero CLI status.
- [ ] Write manifests with dataset, label, sample count, seed, LLM/embedding model, normalization, clustering method, k range, selected k, and prompt hashes; exclude API keys.
- [ ] Document the exact stage commands, environment variables, output tree, hard gates, mock-vs-real-run distinction, and no full experiment claim without real API/model execution.
- [ ] Run tests/induction and then the complete existing suite. Expected: zero failures.
- [ ] Commit with message feat: expose hard-gated induction pipeline.

### Task 7: Remove graph assets and trim CMPV traces

**Files:**
- Delete: src/property_graph/
- Delete: tests/property_graph/
- Delete: configs/property_graph.yaml
- Delete: docs/superpowers/specs/2026-09-28-property-graph-induction-design.md
- Delete: docs/superpowers/plans/2026-09-28-property-graph-induction.md
- Delete generated: runs/property-graph-smoke/ and runs/property-graph-smoke-live/
- Delete generated: traces/*.yaml under every runs directory whose name contains cmpv
- Modify: pyproject.toml and README.md

- [ ] Add a regression test asserting pyproject.toml has no property_graph entry point and run it before deletion to observe failure.
- [ ] Use apply_patch for tracked removals. Verify every generated deletion target resolves under the repository runs directory before removal. Delete only the two explicit graph runs and CMPV trace children; retain CMPV manifest/metrics/predictions/audit files.
- [ ] Run rg for property-graph references in runtime/config/tests/docs and verify no runtime references remain. Run full pytest and verify all tests pass.
- [ ] Commit with message chore: remove property graph and trim cmpv traces.

## Final verification checklist

- [ ] git status --short contains only intentional changes.
- [ ] No tracked property-graph source, test, config, or CLI entry remains.
- [ ] CMPV summaries remain and all CMPV trace YAML files are gone.
- [ ] Existing and induction tests pass.
- [ ] No full LLM/Hugging Face experiment is claimed unless a real run was executed.

