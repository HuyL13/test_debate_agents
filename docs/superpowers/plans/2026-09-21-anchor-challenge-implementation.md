# Anchor-and-Challenge Multi-Agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and run a multi-perspective Anchor-and-Challenge pipeline for CoCoLoFa detection and classification while preserving the repository's existing metrics and artifacts.

**Architecture:** A direct anchor creates the initial judgment, a structural verifier and contextual critic independently test it, deterministic routing opens at most two targeted debates, and a symmetric judge produces the final result. The existing conflict-guided and single-LLM runners remain unchanged so all three methods can be compared.

**Tech Stack:** Python 3.11, PyYAML, existing OpenAI-compatible `Client`, pytest.

**Spec:** `docs/superpowers/specs/2026-09-21-anchor-challenge-design.md`

## Global Constraints

- Model-visible input contains only title, parent comment, target comment, and generated reports; never gold labels or annotation metadata.
- Evidence must resolve to target-only evidence IDs using the existing evidence utilities.
- Detection always compares explicit `Fallacious` and `Non-Fallacious` hypotheses.
- Detection perspectives produce at most one candidate each.
- Classification adjudication receives at most three deduplicated candidates.
- Debate handles at most two conflicts in this order: discourse ownership, inference existence, subtype discrimination.
- Unresolved debate preserves the anchor.
- Final verification is deterministic and makes no LLM call.
- Existing conflict-guided and single-LLM code paths remain runnable.
- Runs emit the existing metrics, manifest, predictions, samples, audit, and YAML trace artifacts.

---

### Task 1: Stage Schemas And Semantic Contracts

**Files:**
- Create: `src/deliberation_schemas.py`
- Create: `tests/test_deliberation_schemas.py`

**Interfaces:**
- Produces: `anchor_schema(task)`, `structural_verifier_schema(task)`, `contextual_critic_schema(task)`, `debate_schema()`, and `judge_schema(task, candidates)` returning strict JSON schemas.
- Produces: `validate_anchor`, `validate_structural_verifier`, `validate_contextual_critic`, and `validate_judge` semantic validators.
- Consumes: `labels_for`, `object_schema`, `validate_output`, and existing target evidence validation.

- [ ] **Step 1: Write failing schema and semantic-validation tests**

Cover these observable contracts with literal fixtures:

```python
def test_detection_anchor_rejects_candidate_for_negative_verdict():
    value = detection_anchor(verdict="Non-Fallacious", primary_candidate="False Dilemma")
    with pytest.raises(ValueError, match="negative anchor"):
        validate_anchor(value, "detection")


def test_classification_anchor_allows_one_distinct_alternative():
    value = classification_anchor(
        primary="False Dilemma",
        alternative="Hasty Generalization",
        ambiguity="The scope of the conclusion is ambiguous.",
    )
    assert validate_anchor(value, "classification") == value


def test_judge_rejects_positive_detection_without_satisfied_structure():
    value = detection_judgment(
        verdict="Fallacious",
        candidate="False Dilemma",
        structural_confirmation=False,
    )
    with pytest.raises(ValueError, match="structural confirmation"):
        validate_judge(value, "detection", ["False Dilemma"], anchor_verdict="Non-Fallacious")
```

- [ ] **Step 2: Run the focused tests and verify RED**

Run: `pytest -q tests/test_deliberation_schemas.py`

Expected: collection fails because `src.deliberation_schemas` does not exist.

- [ ] **Step 3: Implement strict schemas and validators**

Use `additionalProperties: false`, exact enums from `labels_for`, bounded strings, and target evidence IDs. Keep semantic rules in named validators rather than prompt text alone. Expose these signatures:

```python
def anchor_schema(task: str) -> dict: ...
def structural_verifier_schema(task: str) -> dict: ...
def contextual_critic_schema(task: str) -> dict: ...
def debate_schema() -> dict: ...
def judge_schema(task: str, candidates: list[str]) -> dict: ...

def validate_anchor(value: dict, task: str) -> dict: ...
def validate_structural_verifier(value: dict, task: str) -> dict: ...
def validate_contextual_critic(value: dict, task: str) -> dict: ...
def validate_judge(
    value: dict,
    task: str,
    candidates: list[str],
    *,
    anchor_verdict: str,
) -> dict: ...
```

- [ ] **Step 4: Run focused and existing schema tests**

Run: `pytest -q tests/test_deliberation_schemas.py tests/test_schemas.py`

Expected: all tests pass.

- [ ] **Step 5: Commit the contracts**

```powershell
git add src/deliberation_schemas.py tests/test_deliberation_schemas.py
git commit -m "feat: define deliberation stage contracts"
```

### Task 2: Prompts, Hypotheses, And Disagreement Routing

**Files:**
- Create: `src/deliberation_prompts.py`
- Create: `src/deliberation_routing.py`
- Create: `tests/test_deliberation_routing.py`

**Interfaces:**
- Produces: `prompt_for(role, task)` for `anchor`, `structural_verifier`, `contextual_critic`, `debate`, and `judge`.
- Produces: `build_hypotheses(task, anchor, structural, contextual) -> dict`.
- Produces: `route_disagreements(task, anchor, structural, contextual) -> list[dict]` with at most two ordered conflicts.
- Produces: `candidate_union(task, anchor, structural, contextual) -> list[str]` capped at three labels for classification.

- [ ] **Step 1: Write failing routing tests**

```python
def test_detection_routes_ownership_before_inference_conflict():
    conflicts = route_disagreements(
        "detection",
        positive_anchor("False Dilemma"),
        rejected_structure("False Dilemma"),
        contextual_negative(owned=False),
    )
    assert [item["claim"] for item in conflicts] == [
        "target_owns_claim",
        "inference_exists",
    ]


def test_classification_candidate_union_is_deduplicated_and_capped():
    candidates = candidate_union(
        "classification",
        classification_anchor("False Dilemma", "Hasty Generalization"),
        replacement_structure("Slippery Slope"),
        contextual_candidate("Appeal to Worse Problems"),
    )
    assert candidates == ["False Dilemma", "Hasty Generalization", "Slippery Slope"]


def test_no_disagreement_skips_debate():
    assert route_disagreements(
        "detection",
        positive_anchor("Slippery Slope"),
        confirmed_structure("Slippery Slope"),
        contextual_positive("Slippery Slope"),
    ) == []
```

- [ ] **Step 2: Run the focused tests and verify RED**

Run: `pytest -q tests/test_deliberation_routing.py`

Expected: collection fails because routing functions do not exist.

- [ ] **Step 3: Implement deterministic routing and hypothesis construction**

Use a fixed priority table:

```python
CONFLICT_PRIORITY = (
    "target_owns_claim",
    "inference_exists",
    "subtype_discrimination",
)
MAX_DEBATES = 2
MAX_CLASSIFICATION_CANDIDATES = 3
```

Prompts must describe role-specific objectives, require target evidence IDs, prohibit hidden annotation use, and tell each role not to imitate the other roles. The contextual critic must seek a charitable non-fallacious reading rather than search for a reasoning defect.

- [ ] **Step 4: Run routing tests**

Run: `pytest -q tests/test_deliberation_routing.py`

Expected: all tests pass.

- [ ] **Step 5: Commit prompts and routing**

```powershell
git add src/deliberation_prompts.py src/deliberation_routing.py tests/test_deliberation_routing.py
git commit -m "feat: route targeted deliberation conflicts"
```

### Task 3: Anchor-And-Challenge Engine

**Files:**
- Create: `src/deliberation_engine.py`
- Create: `tests/test_deliberation_engine.py`

**Interfaces:**
- Consumes all contracts and routing functions from Tasks 1 and 2.
- Consumes `LLM.generate`, `ModelInput`, `target_passages`, and existing call-stat aggregation.
- Produces `DeliberationEngine(client, task).run(model_input, metadata) -> dict`.
- Result keys: `anchor`, `structural_verifier`, `contextual_critic`, `hypotheses`, `disagreements`, `debates`, `judge`, `selected_candidate`, `prediction`, and `stats`.

- [ ] **Step 1: Write failing orchestration tests with a recording LLM**

Test real engine behavior at the LLM boundary:

```python
def test_agreement_skips_debate_and_calls_judge():
    llm = ScriptedLLM([
        positive_anchor_output("Slippery Slope"),
        confirmed_structure_output("Slippery Slope"),
        contextual_positive_output("Slippery Slope"),
        positive_judge_output("Slippery Slope"),
    ])
    result = DeliberationEngine(llm, "detection").run(INPUT, META)
    assert [call["metadata"]["stage"] for call in llm.calls] == [
        "anchor", "structural_verifier", "contextual_critic", "judge"
    ]
    assert result["debates"] == []
    assert result["prediction"] == "Fallacious"


def test_disagreement_runs_at_most_two_targeted_debates():
    result = run_scripted_conflict_case()
    assert len(result["debates"]) == 2
    assert [item["claim"] for item in result["debates"]] == [
        "target_owns_claim", "inference_exists"
    ]


def test_unresolved_debate_preserves_anchor():
    result = run_unresolved_negative_anchor_case()
    assert result["prediction"] == "Non-Fallacious"
    assert result["judge"]["selected_candidate"] is None


def test_model_payload_never_contains_gold_or_annotation_metadata():
    llm, result = run_scripted_case(metadata={"sample_id": "1:2", "split": "test"})
    serialized = json.dumps([call["user_prompt"] for call in llm.calls])
    assert '"gold"' not in serialized
    assert "worker_id" not in serialized
```

- [ ] **Step 2: Run engine tests and verify RED**

Run: `pytest -q tests/test_deliberation_engine.py`

Expected: collection fails because `DeliberationEngine` does not exist.

- [ ] **Step 3: Implement the engine in explicit stages**

Implement private methods `_call`, `_run_perspectives`, `_run_debates`, and `_judge`. Run the three initial perspectives independently from raw input; do not expose one initial report to another. Every call receives evidence IDs resolved through the existing evidence utilities. Aggregate all `GenerationResult` objects into the existing stats shape.

Apply deterministic post-judge verification:

```python
def verify_final_result(task, anchor, structural, judge):
    if task == "detection" and judge["selected_verdict"] == "Fallacious":
        if judge["selected_candidate"] is None:
            raise ValueError("Positive verdict requires candidate")
        if anchor["verdict"] == "Non-Fallacious" and not structural["condition_satisfied"]:
            raise ValueError("Positive override requires structural confirmation")
    if task == "detection" and judge["selected_verdict"] == "Non-Fallacious":
        if judge["selected_candidate"] is not None:
            raise ValueError("Negative verdict cannot select candidate")
```

- [ ] **Step 4: Run engine and existing engine tests**

Run: `pytest -q tests/test_deliberation_engine.py tests/test_engine.py tests/test_evidence_ids.py`

Expected: all tests pass.

- [ ] **Step 5: Commit the engine**

```powershell
git add src/deliberation_engine.py tests/test_deliberation_engine.py
git commit -m "feat: add anchor-and-challenge engine"
```

### Task 4: Runner, Traces, And Configuration

**Files:**
- Create: `src/deliberation_run.py`
- Create: `configs/deliberation_detection.yaml`
- Create: `configs/deliberation_classification.yaml`
- Create: `tests/test_deliberation_runner.py`
- Modify: `README.md`

**Interfaces:**
- Produces CLI: `python -m src.deliberation_run --config PATH --split test --output NAME [--resume]`.
- Produces the existing run artifact names and metric schema.
- Consumes `load_config`, `load_split`, `select_task`, `score`, `Client`, and `DeliberationEngine`.

- [ ] **Step 1: Write failing runner tests**

```python
def test_runner_writes_complete_detection_artifacts(tmp_path):
    result = execute(config(tmp_path, task="detection"), client=scripted_client())
    run = tmp_path / "runs" / "deliberation-smoke"
    assert result["status"] == "complete"
    assert (run / "manifest.json").exists()
    assert (run / "metrics.json").exists()
    assert (run / "predictions.jsonl").exists()
    assert (run / "samples.csv").exists()
    assert len(list((run / "traces").glob("*.yaml"))) == 2


def test_resume_skips_completed_trace_without_duplicate_csv_row(tmp_path):
    cfg = config(tmp_path, task="detection")
    execute(cfg, limit=1, client=scripted_client())
    before = (run_dir(cfg) / "samples.csv").read_text(encoding="utf-8")
    execute(cfg, limit=1, resume=True, client=client_that_must_not_be_called())
    assert (run_dir(cfg) / "samples.csv").read_text(encoding="utf-8") == before
```

- [ ] **Step 2: Run runner tests and verify RED**

Run: `pytest -q tests/test_deliberation_runner.py`

Expected: collection fails because `src.deliberation_run` does not exist.

- [ ] **Step 3: Implement runner and trace output**

Reuse existing output-directory safety, resume manifest checks, strict failure handling, and metric scoring. Each YAML trace must include all engine stages and the standard stats fields. Set both configs to the same `NVIDIA_MODEL`, `NVIDIA_BASE_URL`, and `NVIDIA_API_KEY` environment variables used by existing runs.

Document these commands:

```powershell
python -m src.deliberation_run --config configs/deliberation_detection.yaml --split test --output detection-test-anchor-challenge
python -m src.deliberation_run --config configs/deliberation_classification.yaml --split test --output classification-test-anchor-challenge
```

- [ ] **Step 4: Run runner tests and CLI smoke checks**

Run:

```powershell
pytest -q tests/test_deliberation_runner.py
python -m src.deliberation_run --help
```

Expected: tests pass and help lists `--config`, `--split`, `--limit`, `--output`, and `--resume`.

- [ ] **Step 5: Commit runner and configs**

```powershell
git add src/deliberation_run.py configs/deliberation_detection.yaml configs/deliberation_classification.yaml tests/test_deliberation_runner.py README.md
git commit -m "feat: add anchor-and-challenge runner"
```

### Task 5: Full Verification And Test Runs

**Files:**
- Generated: `runs/detection-test-anchor-challenge/`
- Generated: `runs/classification-test-anchor-challenge/`

**Interfaces:**
- Consumes the completed runner and configurations.
- Produces complete test metrics and per-sample traces for both tasks.

- [ ] **Step 1: Run the full automated test suite**

Run: `pytest -q`

Expected: zero failures.

- [ ] **Step 2: Run full detection**

```powershell
python -m src.deliberation_run --config configs/deliberation_detection.yaml --split test --output detection-test-anchor-challenge
```

If interrupted, resume with the identical command plus `--resume`. Continue until `metrics.json` reports `status: complete` and count `798`.

- [ ] **Step 3: Run full classification**

```powershell
python -m src.deliberation_run --config configs/deliberation_classification.yaml --split test --output classification-test-anchor-challenge
```

If interrupted, resume with the identical command plus `--resume`. Continue until `metrics.json` reports `status: complete` and count `481`.

- [ ] **Step 4: Validate generated artifacts and report existing metrics**

Confirm trace counts equal metric counts, no failed samples exist, and report:

- detection accuracy, precision, recall, F1, false-positive rate, false-negative rate, and confusion matrix;
- classification accuracy, macro-F1, per-label scores, and confusion matrix;
- logical calls, provider calls, total tokens, and summed wall time for both runs;
- direct comparison with `detection-test-single-llm`, `detection-test`, `classification-test-single-llm`, and `classification-test`.

- [ ] **Step 5: Commit completed run artifacts only after verifying no raw API or secrets**

```powershell
git add -f runs/detection-test-anchor-challenge runs/classification-test-anchor-challenge
git commit -m "results: add anchor-and-challenge test traces"
```
