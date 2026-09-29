# Unified Adjudication Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace destructive resolver-plus-arbiter processing with three balanced independent reports and one comparative final adjudicator.

**Architecture:** Extend the existing analyst contracts, retain all proposed hypotheses in candidate dossiers, and make one final call over candidates plus an explicit negative detection hypothesis. Preserve the current runner and metrics surface.

**Tech Stack:** Python 3.11, JSON Schema, PyYAML, pytest, existing OpenAI-compatible LLM client.

**Spec:** `docs/superpowers/specs/2026-09-21-unified-adjudication-design.md`

## Global Constraints

- Keep `structure`, `goal`, and `counterargument` as independent first-stage calls.
- Remove semantic resolver calls and destructive candidate elimination.
- Detection always compares against an explicit `Non-Fallacious` hypothesis.
- Keep existing benchmark metrics and label space.
- Do not add dependencies or use a worktree.

---

### Task 1: Analyst And Final Schemas

**Files:**
- Modify: `src/schemas.py`
- Modify: `tests/test_schemas.py`

**Interfaces:**
- Produces: consistent analyst reports and `comparative_adjudicator_schema(task, candidates)`.

- [ ] Add failing schema and semantic-validation tests for verdict/candidate consistency, opposing reasons, counterargument defense, and final allowed choices.
- [ ] Run `pytest -q tests/test_schemas.py` and confirm the new tests fail for missing contracts.
- [ ] Implement the minimum schema and validators.
- [ ] Run `pytest -q tests/test_schemas.py` and confirm all tests pass.
- [ ] Commit schema changes.

### Task 2: Candidate Dossiers And Routing

**Files:**
- Create: `src/adjudication.py`
- Create: `tests/test_adjudication.py`

**Interfaces:**
- Produces: `build_candidate_dossiers(task, reports)` and `adjudication_route(task, dossiers)`.

- [ ] Add failing tests proving contested candidates survive, label conditions stay attached to their source label, and detection always routes to final adjudication.
- [ ] Run `pytest -q tests/test_adjudication.py` and verify RED.
- [ ] Implement dossier construction and classification singleton routing.
- [ ] Run `pytest -q tests/test_adjudication.py` and verify GREEN.
- [ ] Commit dossier changes.

### Task 3: Balanced Prompts

**Files:**
- Modify: `src/prompts.py`
- Modify: `tests/test_prompt_contracts.py`

**Interfaces:**
- Produces: role prompts matching the schemas and a `comparative_arbiter` prompt with contrastive label tests.

- [ ] Add failing behavior tests that run fixture outputs through each role's contract.
- [ ] Run the focused tests and verify RED.
- [ ] Update analyst and comparative-adjudicator prompts.
- [ ] Run the focused tests and verify GREEN.
- [ ] Commit prompt changes.

### Task 4: Unified Engine

**Files:**
- Modify: `src/engine.py`
- Modify: `tests/test_engine.py`

**Interfaces:**
- Consumes: analyst validators, `build_candidate_dossiers`, and `adjudication_route`.
- Produces: the existing result envelope with `candidate_state.dossiers`, no resolver calls, and comparative final adjudication.

- [ ] Add failing engine tests for four-call detection, no destructive pruning, negative recovery, classification singleton shortcut, and comparative classification.
- [ ] Run `pytest -q tests/test_engine.py` and verify RED.
- [ ] Replace conflict resolution and the old arbiter path with unified adjudication.
- [ ] Run `pytest -q tests/test_engine.py` and verify GREEN.
- [ ] Commit engine changes.

### Task 5: Runner And Documentation

**Files:**
- Modify: `src/runner.py`
- Modify: `tests/test_runner.py`
- Modify: `docs/METHOD.md`
- Modify: `README.md`

**Interfaces:**
- Preserves: CLI commands, metrics, resume behavior, trace writing, and progress output.

- [ ] Add failing runner tests for dossiers, final-stage logging, and unchanged metrics artifacts.
- [ ] Run focused runner tests and verify RED.
- [ ] Update trace/CSV/log output and method documentation.
- [ ] Run focused runner tests and verify GREEN.
- [ ] Commit runner changes.

### Task 6: Verification And API Smoke Tests

**Files:**
- No production files unless a demonstrated defect requires a new TDD cycle.

**Interfaces:**
- Verifies the complete feature.

- [ ] Run `pytest -q` and `git diff --check`.
- [ ] Run one real detection smoke sample and inspect all four stage outputs.
- [ ] Run one real classification smoke sample and inspect routing and final output.
- [ ] Re-run `pytest -q` after any API-driven fix.
- [ ] Record final branch status and commands for full test evaluation.
