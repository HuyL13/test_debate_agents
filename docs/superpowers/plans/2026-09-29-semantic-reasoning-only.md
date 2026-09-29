# Semantic Reasoning-Only Records Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (or subagent-driven-development) to implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Goal:** Replace verbose semantic extraction records with `{sample_id, original_text, canonical_reasoning}` and preserve the full inferential relation in natural-language reasoning.

**Architecture:** The semantic LLM stage emits only the minimal persisted contract. Local validation enforces exact fields, natural canonical prose, detopicalization, and sample-key uniqueness. Audit, embedding, resume, mock transport, clustering diagnostics, and tests consume the reduced contract without reconstructing removed semantic fields.

**Tech Stack:** Python 3.11, existing JSON-schema validation, pytest, NumPy, scikit-learn, and the existing structured LLM client.

**Spec:** `docs/superpowers/specs/2026-09-29-semantic-reasoning-only-design.md`

## Global Constraints

- Persist exactly `sample_id`, `original_text`, and `canonical_reasoning` for successful semantic records.
- Embed only `canonical_reasoning`.
- Do not mechanically replace every noun with an uppercase token.
- Do not include named hard cases as production few-shot examples.
- Do not migrate old verbose records by inventing or rewriting semantic content locally.
- Do not call an external LLM or Hugging Face service during tests or this implementation.

---

### Task 1: Replace the semantic contract and quality checks

**Files:**
- Modify: `src/induction/contracts.py`
- Modify: `tests/induction/test_config_data_contracts.py`

**Interfaces:**
- `semantic_schema() -> dict` exposes only `sample_id`, `original_text`, and `canonical_reasoning`.
- `validate_semantic_record(record, sample) -> dict` validates the exact minimal contract.

- [x] Write failing tests for rejecting `premise`, `conclusion`, `direction`, `ambiguity_notes`, and every other extra semantic field.
- [x] Write failing tests for short/tag-only canonical text and more than two distinct underscore-style uppercase placeholders.
- [x] Write a passing fixture with a natural canonical representation that preserves the bridge and direction without separate direction fields.
- [x] Run `\.venv\Scripts\python.exe -m pytest -q tests/induction/test_config_data_contracts.py` and confirm the new tests fail for the old contract.
- [x] Implement the minimal schema and validation checks without fabricating or transforming semantic content.
- [x] Run the focused test file and confirm all tests pass.

### Task 2: Replace the extraction prompt, resume key, and mock output

**Files:**
- Modify: `src/induction/prompts.py`
- Modify: `src/induction/semantic.py`
- Modify: `src/llm/mock.py`
- Modify: `tests/induction/test_semantic_extraction.py`

**Interfaces:**
- `semantic_extraction_prompt(sample, use_parent_context=False) -> (str, str)` requests the minimal contract and performs reasoning before abstraction.
- `extract_semantic_records(config, samples, client, resume=False) -> list[dict]` keys completed records by `sample_id`.

- [x] Write failing prompt tests requiring the seven-step reasoning order, natural abstractions, no mechanical entity replacement, and no hard-case few-shot IDs.
- [x] Write failing resume tests proving stale verbose records are removed and duplicate minimal records collapse to one `sample_id`.
- [x] Update the mock semantic response to emit only the three fields.
- [x] Implement prompt text from the approved guideline, retaining bridge and direction inside `canonical_reasoning`.
- [x] Bind and validate `sample_id`/`original_text`, normalize only transport-level JSON values, and remove stale records through the existing keyed resume path.
- [x] Run `\.venv\Scripts\python.exe -m pytest -q tests/induction/test_semantic_extraction.py` and confirm all tests pass.

### Task 3: Adapt semantic audit and clustering diagnostics

**Files:**
- Modify: `src/induction/audit.py`
- Modify: `src/induction/clustering.py`
- Modify: `tests/induction/test_semantic_audit_embedding.py`
- Modify: `tests/induction/test_clustering.py`

**Interfaces:**
- `audit_semantics(config) -> dict` indexes records by `sample_id` and audits the minimal contract.
- `search_k(config, embeddings, records) -> dict` writes clustering diagnostics without removed field purity metrics.

- [x] Write failing audit tests for missing/extra fields, stale verbose records, copied canonical text, and representation collapse.
- [x] Write a failing clustering test proving metrics no longer require `relation_polarity`, `conclusion_direction`, or `premise_valence`.
- [x] Implement sample-id indexing, minimal-record completeness checks, and natural-canonical quality reporting.
- [x] Remove purity columns that depended on deleted fields while preserving cluster size, silhouette, and distance diagnostics.
- [x] Run the focused audit and clustering tests and confirm all pass.

### Task 4: Update documentation and run the complete verification suite

**Files:**
- Modify: `README.md`
- Modify: `docs/superpowers/specs/2026-09-29-semantic-induction-design.md`
- Modify: `src/induction/embedding.py` only if the reduced-record audit exposes a compatibility issue.

- [x] Document the exact three-field semantic record and state that only `canonical_reasoning` is embedded.
- [x] Document that old verbose records are stale and must be regenerated, not locally migrated.
- [x] Run `\.venv\Scripts\python.exe -m pytest -q`.
- [x] Run `git diff --check`.
- [x] Inspect `git status --short` and confirm only intentional files changed.
