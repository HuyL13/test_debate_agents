# Property Graph Induction Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Goal:** Build and smoke-test a train-only, definition-initialized CoCoLoFa fallacy property graph with LLM signatures, deterministic induction/retrieval, and seed-to-evolved reporting.

**Architecture:** Add an isolated src/property_graph package that reuses the current data loader and LLM client. The LLM only emits argument signatures; deterministic code owns graph construction, indexing, retrieval, versioning, and comparison.

**Tech Stack:** Python 3.11+, stdlib, PyYAML, existing src.llm.Client, pytest.

**Spec:** docs/superpowers/specs/2026-09-28-property-graph-induction-design.md

## Global Constraints

- Work directly on feat/new-method; never create or use Git worktrees.
- Load NVIDIA_API_KEY, NVIDIA_BASE_URL, and NVIDIA_MODEL from the current .env; never persist secrets.
- Use positive classification-train samples only; never induce or tune with test.
- Extraction sees title, parent, and target only—never gold/candidate labels or definitions.
- Make one logical Client.generate call per sample; provider retries stay inside Client.
- JSON remains the graph source of truth; no Neo4j, GNN, embeddings, multi-agent extraction, or online mutation.
- Follow TDD and keep the existing suite green.
- Live verification uses 8–16 samples, not the full 3,168.

---

### Task 1: Signature and Graph Contracts

**Files:**
- Create: src/property_graph/__init__.py
- Create: src/property_graph/schemas.py
- Create: tests/property_graph/test_schemas.py

**Interfaces:**
- Produces SIGNATURE_JSON_SCHEMA, validate_signature(signature, visible_text), validate_graph(graph), and slug(value).
- Consumes src.schemas.validate_output.

- [ ] **Step 1: Write failing contract tests**

~~~python
def test_signature_rejects_missing_endpoint(valid_signature):
    valid_signature["relations"][0]["target"] = "missing"
    with pytest.raises(ValueError, match="relation endpoint"):
        validate_signature(valid_signature, "Experts agree. It is true.")

def test_signature_rejects_unseen_evidence(valid_signature):
    valid_signature["relations"][0]["evidence_spans"] = ["gold says so"]
    with pytest.raises(ValueError, match="evidence span"):
        validate_signature(valid_signature, "Experts agree. It is true.")

def test_graph_rejects_dangling_edge():
    graph = {"meta": {}, "nodes": [], "edges": [{
        "id": "e1", "source": "missing", "target": "also-missing",
        "type": "HAS_PROTOTYPE", "weight": 1.0,
        "support_count": 0, "attrs": {}, "provenance": []}]}
    with pytest.raises(ValueError, match="endpoint"):
        validate_graph(graph)
~~~

- [ ] **Step 2: Run RED**

Run: .\.venv\Scripts\python.exe -m pytest tests/property_graph/test_schemas.py -q

Expected: ModuleNotFoundError for src.property_graph.

- [ ] **Step 3: Implement strict JSON schema and semantic checks**

Define enums for all guide vocabularies. Validate unique proposition/node/edge IDs, relation and edge endpoints, evidence spans, locked labels, finite weights, non-negative support, and provenance on induced objects.

~~~python
def validate_signature(signature, visible_text):
    validate_output(signature, SIGNATURE_JSON_SCHEMA)
    ids = [item["id"] for item in signature["propositions"]]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate proposition id")
    for relation in signature["relations"]:
        if relation["source"] not in ids or relation["target"] not in ids:
            raise ValueError("relation endpoint does not exist")
        if any(span not in visible_text for span in relation["evidence_spans"]):
            raise ValueError("evidence span is not present in visible text")
~~~

- [ ] **Step 4: Run GREEN and commit**

Run: .\.venv\Scripts\python.exe -m pytest tests/property_graph/test_schemas.py -q
Expected: PASS.

~~~powershell
git add src/property_graph tests/property_graph/test_schemas.py
git commit -m "feat: define property graph contracts"
~~~

### Task 2: Seed Graph and Graph I/O

**Files:**
- Create: definitions/fallacy_labels.json
- Create: src/property_graph/seed.py
- Create: src/property_graph/graph_io.py
- Create: tests/property_graph/test_seed_and_io.py

**Interfaces:**
- Produces load_definitions, build_seed_graph, load_graph, save_graph, build_node_map, build_adjacency, get_neighbors, and get_label_subgraph.

- [ ] **Step 1: Write failing seed and round-trip test**

~~~python
def test_seed_has_locked_labels_and_round_trips(tmp_path):
    graph = build_seed_graph(load_definitions("definitions/fallacy_labels.json"),
                             {"graph_version": "seed"})
    labels = [n for n in graph["nodes"] if n["type"] == "label"]
    assert {n["name"] for n in labels} == set(FALLACIES)
    assert all(n["attrs"]["locked"] is True for n in labels)
    path = tmp_path / "seed.json"
    save_graph(graph, path)
    assert load_graph(path) == graph
~~~

- [ ] **Step 2: Run RED**

Run: .\.venv\Scripts\python.exe -m pytest tests/property_graph/test_seed_and_io.py -q
Expected: missing seed/I/O modules.

- [ ] **Step 3: Implement eight definitions, stable IDs, navigation, and atomic validated JSON writes**

Each definition contains label, immutable definition, mechanisms, and conditions. Generate sorted stable IDs such as label:appeal_to_authority.

~~~python
def get_neighbors(graph, node_id, edge_types=None):
    allowed = set(edge_types) if edge_types is not None else None
    return [edge for edge in graph["edges"]
            if (edge["source"] == node_id or edge["target"] == node_id)
            and (allowed is None or edge["type"] in allowed)]
~~~

- [ ] **Step 4: Run GREEN and commit**

Run: .\.venv\Scripts\python.exe -m pytest tests/property_graph/test_seed_and_io.py tests/property_graph/test_schemas.py -q
Expected: PASS.

~~~powershell
git add definitions src/property_graph/seed.py src/property_graph/graph_io.py tests/property_graph/test_seed_and_io.py
git commit -m "feat: build definition seed graph"
~~~

### Task 3: Leakage-Safe Signature Extraction

**Files:**
- Create: src/property_graph/extraction.py
- Create: tests/property_graph/test_extraction.py
- Modify: src/llm/mock.py

**Interfaces:**
- Produces build_extraction_prompts, extract_signature, and extract_samples.
- Consumes Sample, Client.generate, SIGNATURE_JSON_SCHEMA, and validate_signature.

- [ ] **Step 1: Write failing prompt-boundary test**

~~~python
def test_extraction_hides_gold_and_calls_once(sample, valid_signature):
    client = CapturingClient(valid_signature)
    record, _ = extract_signature(sample, client, "v1")
    assert len(client.calls) == 1
    serialized = json.dumps(client.calls[0])
    assert sample.fallacy not in serialized
    assert all(label not in serialized for label in FALLACIES)
    assert record["gold_label"] == sample.fallacy
~~~

- [ ] **Step 2: Run RED**

Run: .\.venv\Scripts\python.exe -m pytest tests/property_graph/test_extraction.py -q
Expected: missing extraction module.

- [ ] **Step 3: Implement one-call extraction and attach gold afterward**

~~~python
result = client.generate(
    system_prompt=SYSTEM_PROMPT,
    user_prompt=json.dumps(visible, ensure_ascii=False),
    schema=SIGNATURE_JSON_SCHEMA,
    metadata={"stage": "property_graph_extraction",
              "sample_id": sample.sample_id, "split": sample.split,
              "prompt_version": prompt_version,
              "schema_version": SIGNATURE_SCHEMA_VERSION},
    validator=lambda value: validate_signature(value, "\n".join(visible.values())),
)
record = {"sample_id": sample.sample_id, "raw_signature": result.output,
          "gold_label": sample.fallacy, "split": sample.split}
~~~

Implement JSONL resume by sample ID. Terminal errors append sample_id/error, continue, and emit no synthetic signature.

- [ ] **Step 4: Test resume/failure continuation and extend MockTransport**

Add tests proving completed samples skip, failures do not stop later samples, and mock extraction never reads gold.

Run: .\.venv\Scripts\python.exe -m pytest tests/property_graph/test_extraction.py tests/test_llm.py -q
Expected: PASS.

- [ ] **Step 5: Commit**

~~~powershell
git add src/property_graph/extraction.py src/llm/mock.py tests/property_graph/test_extraction.py
git commit -m "feat: extract leakage-safe argument signatures"
~~~

### Task 4: Normalize and Induce Within-Label Prototypes

**Files:**
- Create: src/property_graph/normalization.py
- Create: src/property_graph/induction.py
- Create: tests/property_graph/test_normalization.py
- Create: tests/property_graph/test_induction.py

**Interfaces:**
- Produces normalize_signature, structural_similarity, cluster_signatures, and induce_within_label.

- [ ] **Step 1: Write failing normalization test**

~~~python
def test_normalization_emits_structure_not_text(valid_signature):
    features = normalize_signature(valid_signature)
    assert "REL:USED_AS_JUSTIFICATION" in features
    assert "ROLE:premise->conclusion" in features
    assert "SOURCE_TYPE:expert" in features
    assert not any("Experts agree" in f for f in features)
    assert features == sorted(set(features))
~~~

- [ ] **Step 2: Run RED, implement controlled structural features, then GREEN**

Run: .\.venv\Scripts\python.exe -m pytest tests/property_graph/test_normalization.py -q

- [ ] **Step 3: Write failing prototype/outlier test**

~~~python
def test_within_label_has_provenance_and_outlier(seed_graph):
    records = [record("1", "Appeal to Authority", ["REL:APPEALS_TO_SOURCE", "SOURCE_TYPE:expert"]),
               record("2", "Appeal to Authority", ["REL:APPEALS_TO_SOURCE", "SOURCE_TYPE:expert"]),
               record("3", "Appeal to Authority", ["REL:ATTACKS"])]
    graph, audit = induce_within_label(seed_graph, records, config(min_cluster_size=2))
    prototype = next(n for n in graph["nodes"] if n["type"] == "prototype")
    assert prototype["attrs"]["source_sample_ids"] == ["1", "2"]
    assert audit["Appeal to Authority"]["outlier_sample_ids"] == ["3"]
~~~

- [ ] **Step 4: Run RED; implement weighted family Jaccard, stable threshold components, frequency tiers, medoids, prototypes, edges, and outlier audit; run GREEN**

Run: .\.venv\Scripts\python.exe -m pytest tests/property_graph/test_normalization.py tests/property_graph/test_induction.py -q
Expected: PASS after implementation.

- [ ] **Step 5: Commit**

~~~powershell
git add src/property_graph/normalization.py src/property_graph/induction.py tests/property_graph/test_normalization.py tests/property_graph/test_induction.py
git commit -m "feat: induce fallacy prototypes"
~~~

### Task 5: Cross-Label Evolution and Graph Diff

**Files:**
- Modify: src/property_graph/induction.py
- Create: src/property_graph/reporting.py
- Modify: tests/property_graph/test_induction.py
- Create: tests/property_graph/test_reporting.py

**Interfaces:**
- Produces induce_cross_label, diff_graphs, render_graph_diff, and render_induction_audit.

- [ ] **Step 1: Write failing cross-label test**

~~~python
def test_cross_label_adds_shared_and_discriminative_nodes(prototype_graph, records):
    graph, _ = induce_cross_label(prototype_graph, records, cross_config())
    shared = [n for n in graph["nodes"] if n["type"] == "shared_mechanism"]
    assert shared[0]["attrs"]["shared_by_labels"] == ["appeal_to_authority", "appeal_to_majority"]
    assert shared[0]["attrs"]["provenance"]
    assert any(e["type"] == "DIFFERS_BY" for e in graph["edges"])
~~~

- [ ] **Step 2: Run RED; implement stable shared cores and smoothed log odds; run GREEN**

Run: .\.venv\Scripts\python.exe -m pytest tests/property_graph/test_induction.py -q

- [ ] **Step 3: Write failing diff test**

~~~python
def test_diff_reports_addition_and_edge_update(seed_graph):
    evolved = deepcopy(seed_graph)
    evolved["nodes"].append(induced_prototype("p1", ["s1", "s2"]))
    evolved["edges"][0]["weight"] = 0.75
    diff = diff_graphs(seed_graph, evolved)
    assert diff["added_nodes"][0]["id"] == "p1"
    assert diff["modified_edges"][0]["weight_delta"] == -0.25
    assert diff["locked_seed_invariants"]["violations"] == []
~~~

- [ ] **Step 4: Implement JSON diff and deterministic Markdown**

Include totals/types, additions/removals/modifications, weight/support deltas, prototypes, shared mechanisms, discriminative conditions, provenance, outliers, and locked-label invariants.

Run: .\.venv\Scripts\python.exe -m pytest tests/property_graph/test_induction.py tests/property_graph/test_reporting.py -q
Expected: PASS.

- [ ] **Step 5: Commit**

~~~powershell
git add src/property_graph/induction.py src/property_graph/reporting.py tests/property_graph/test_induction.py tests/property_graph/test_reporting.py
git commit -m "feat: evolve and compare property graphs"
~~~

### Task 6: Indexing and Retrieval

**Files:**
- Create: src/property_graph/indexing.py
- Create: src/property_graph/retrieval.py
- Create: tests/property_graph/test_retrieval.py

**Interfaces:**
- Produces build_indexes, save_indexes, load_indexes, retrieve, and retrieval_metrics.

- [ ] **Step 1: Write failing retrieval and metric tests**

~~~python
def test_retrieval_ranks_and_explains(evolved_graph):
    result = retrieve(signature_with(["REL:APPEALS_TO_SOURCE", "SOURCE_TYPE:expert"]),
                      evolved_graph, build_indexes(evolved_graph), top_k_labels=2)
    top = result["candidate_labels"][0]
    assert top["label"] == "Appeal to Authority"
    assert top["matched_prototypes"]
    assert top["score"] >= result["candidate_labels"][1]["score"]

def test_metrics_reports_recall_and_mrr():
    rows = [{"gold": "A", "ranked_labels": ["B", "A"]},
            {"gold": "C", "ranked_labels": ["C", "A"]}]
    metrics = retrieval_metrics(rows)
    assert metrics["recall_at_1"] == 0.5
    assert metrics["recall_at_2"] == 1.0
    assert metrics["mrr"] == 0.75
~~~

- [ ] **Step 2: Run RED**

Run: .\.venv\Scripts\python.exe -m pytest tests/property_graph/test_retrieval.py -q
Expected: missing modules.

- [ ] **Step 3: Implement indexes, scoring, stable ties, and explanations**

~~~python
score = (weights["required_coverage"] * required_coverage
         + weights["jaccard"] * jaccard
         + weights["typical_coverage"] * typical_coverage
         + weights["discriminative_bonus"] * discriminative_bonus)
~~~

Return shared mechanisms, DIFFERS_BY, representative IDs, matched/missing/contradicting conditions, and query features.

- [ ] **Step 4: Run GREEN and commit**

Run: .\.venv\Scripts\python.exe -m pytest tests/property_graph/test_retrieval.py -q
Expected: PASS.

~~~powershell
git add src/property_graph/indexing.py src/property_graph/retrieval.py tests/property_graph/test_retrieval.py
git commit -m "feat: index and retrieve graph evidence"
~~~

### Task 7: Pipeline, Configuration, and CLI

**Files:**
- Create: configs/property_graph.yaml
- Create: src/property_graph/pipeline.py
- Create: tests/property_graph/test_pipeline.py
- Modify: pyproject.toml

**Interfaces:**
- Produces load_property_graph_config, select_smoke_samples, run_pipeline, and cli.

- [ ] **Step 1: Write failing selection/config tests**

~~~python
def test_smoke_selection_is_train_positive_and_stratified(samples):
    selected = select_smoke_samples(samples, limit=8)
    assert len(selected) == 8
    assert all(s.split == "train" and s.fallacy != "none" for s in selected)
    assert len({s.fallacy for s in selected}) == 8

def test_config_resolves_env_without_storing_secret(monkeypatch):
    monkeypatch.setenv("NVIDIA_MODEL", "model-x")
    monkeypatch.setenv("NVIDIA_BASE_URL", "https://example.test/v1")
    monkeypatch.setenv("NVIDIA_API_KEY", "secret")
    config = load_property_graph_config("configs/property_graph.yaml")
    assert config["model"]["name"] == "model-x"
    assert "secret" not in json.dumps(config)
~~~

- [ ] **Step 2: Run RED**

Run: .\.venv\Scripts\python.exe -m pytest tests/property_graph/test_pipeline.py -q

- [ ] **Step 3: Implement staged orchestration and non-overwriting versions**

~~~python
samples = select_smoke_samples(select_task(load_split(train_path), "classification"), limit)
seed = build_seed_graph(definitions, build_meta(config, samples, "seed"))
records = extract_samples(samples, client, signatures_path, failures_path, resume=resume)
normalized = attach_normalized_features(records)
within, within_audit = induce_within_label(seed, normalized, config["induction"])
evolved, cross_audit = induce_cross_label(within, normalized, config["induction"])
indexes = build_indexes(evolved)
diff = diff_graphs(seed, evolved)
~~~

Validate before writing seed/current/versioned graphs, three indexes, graph_diff JSON/Markdown, audit Markdown, extraction failures/audit, and manifest stats.

- [ ] **Step 4: Add mock end-to-end and CLI tests**

Assert artifacts deserialize, labels remain locked, induced objects have provenance, and diff exists. Commands: prepare, extract, seed, induce, index, retrieve, evaluate, validate, smoke. Add pyproject entry point:

~~~toml
cocolofa-property-graph = "src.property_graph.pipeline:cli"
~~~

Run: .\.venv\Scripts\python.exe -m pytest tests/property_graph/test_pipeline.py -q
Expected: PASS.

- [ ] **Step 5: Full suite and commit**

Run: .\.venv\Scripts\python.exe -m pytest -q
Expected: all tests PASS.

~~~powershell
git add configs/property_graph.yaml src/property_graph/pipeline.py tests/property_graph/test_pipeline.py pyproject.toml
git commit -m "feat: orchestrate property graph pipeline"
~~~

### Task 8: Live Smoke and Evolution Inspection

**Files:**
- Modify: README.md
- Runtime only: runs/property-graph-smoke/
- Test: full suite and live provider smoke.

**Interfaces:**
- Consumes current .env, property-graph config, and data/cocolofa/train.json.
- Produces live artifacts and reproduction documentation.

- [ ] **Step 1: Read test-writing rules and verify suite**

Read C:\Users\yoga\.codex\skills\test-driven-development\writing-good-tests.md and audit new tests.

~~~powershell
.\.venv\Scripts\python.exe -m pytest -q
~~~

Expected: all tests PASS without warnings.

- [ ] **Step 2: Run live train-only smoke**

~~~powershell
.\.venv\Scripts\python.exe -m src.property_graph.pipeline smoke --config configs/property_graph.yaml --limit 8 --output runs/property-graph-smoke --resume
~~~

Expected: exit 0, or provider failures recorded honestly. Never substitute dev/test or expand to full train.

- [ ] **Step 3: Validate and compare seed/evolved graphs**

~~~powershell
.\.venv\Scripts\python.exe -m src.property_graph.pipeline validate --graph runs/property-graph-smoke/seed_graph.json
.\.venv\Scripts\python.exe -m src.property_graph.pipeline validate --graph runs/property-graph-smoke/fallacy_graph.json
Get-Content runs/property-graph-smoke/graph_diff.md
~~~

Confirm totals, additions/modifications, provenance, and locked invariants. Explain zero changes via coverage, cluster size, outlier ratio, and thresholds.

- [ ] **Step 4: Document, re-verify, and commit**

Document commands, artifacts, train-only guarantee, env names, resume/cache, and smoke-not-research warning.

~~~powershell
.\.venv\Scripts\python.exe -m pytest -q
git status --short
git diff --check
git add README.md
git commit -m "docs: document property graph smoke workflow"
~~~

- [ ] **Step 5: Final evidence**

Report test count, sample IDs/label coverage, logical/provider calls, cache hits/retries/tokens/failures, seed/evolved counts by type, prototypes/shared mechanisms/discriminative conditions, modified weights/support, outlier ratios, and artifact links.

