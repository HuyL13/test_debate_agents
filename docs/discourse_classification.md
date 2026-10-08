# Code-first discourse classification

This pipeline implements eight-label CoCoLoFa classification. It does not train a classifier. Gold labels are used only for filtering upstream data, train partitions and metrics, never model prompts.

The default input is the existing upstream train file filtered to positive comments. For a separate classification dataset, pass `--input PATH`; do not assume the default is your separate file. Flat JSON records require `sample_id` or `id`, `comment`, and `gold`, `fallacy` or `label` containing one of the eight labels. Optional `article_id`/`news_id`, `title` and `parent_comment` are supported. Upstream article-list JSON is also supported.

Version 5.0 uses two primary model requests: neutral role extraction, then comparative verification of all eight labels against the comment, proposition graph and matched templates. It replaces v4.5's optional completion and code-only final selection. Retrieval is a fallible aid, not a veto: missing candidates, tied templates and extraction contract failures cannot cause semantic abstention. Extraction failure is retained as `role_extraction_status: failed` while the regular verifier still runs. Legacy recovery remains disabled and unchanged.

The verifier assesses each label exactly once as SUPPORTED, WEAK or ABSENT and selects a required non-null eight-label prediction. It selects a supported interpretation when one exists, otherwise the closest weak interpretation. The chosen assessment cannot be ABSENT and must reference evidence propositions. Code rejects duplicate labels and unknown node IDs, then copies exact proposition spans into final evidence. Weak support never blocks classification. This guarantees a label after valid verification, not correctness of every judgment; genuine provider/contract failures remain retryable errors.

Role extraction still uses grounded short quotes and family-specific attributes. Final verification uses node IDs instead of copied quotes or offsets. Code grounding validates source location, not the semantic correctness of a role or label. Graph relations are heuristic, and missing edges cannot establish that a mechanism is absent.

Metrics include full-selection accuracy/completion rate, matched-template coverage, retrieval failures and decision modes (`verified` or `verified_weak`). Candidate coverage describes retrieval, not final label eligibility. A controlled graph contribution check must rerun the verifier with `--without-relations`; the old offline code-ranking replay is unavailable for verified final decisions.

Historical v4.5 full test: 244 correct, 77 wrong, 157 unresolved and 3 errors out of 481, accuracy 50.73%, macro-F1 0.5872. The previously inspected four test examples make repeat evaluations partially exposed. The initial v5.0 eight-sample train-validation smoke selected all eight labels without errors or recovery, with 5/8 correct; this is not a benchmark. Use fresh run folders across versions.

Install and prepare once:

```powershell
.venv/Scripts/python.exe -m pip install -r requirements-discourse.txt
.venv/Scripts/python.exe -m scripts.discourse_classification --download-models
```

The CLI automatically loads the project `.env` using existing repo code. Model name, endpoint and key come from `NVIDIA_MODEL`, `NVIDIA_BASE_URL`, `NVIDIA_API_KEY`. Keys are not written to results. Edit the config for other environment variable names.

First inspect retrieval without API calls:

```powershell
.venv/Scripts/python.exe -m scripts.discourse_classification --input data/cocolofa/classification/train.json --coverage-only --output graph-coverage
```

Coverage-only inspects legacy rule anchors and deterministic graph relations; it does not run the primary role extractor. Coverage measures whether a gold-label candidate exists, not whether its evidence is correct. Review examples per label in the report. No coverage target or accuracy claim is assumed.

Run a small API smoke test, then expand:

```powershell
.venv/Scripts/python.exe -m scripts.discourse_classification --input data/cocolofa/classification/train.json --limit 8 --output graph-train-smoke
.venv/Scripts/python.exe -m scripts.discourse_classification --input data/cocolofa/classification/train.json --limit 8 --output graph-train-smoke --resume
```

For article-disjoint design/validation partitions of train, use `--partition design` or `--partition validation` with `split: train`. Flat data must include article IDs. The seeded partition is computed from all input articles before `--limit`; no test partition is constructed or tuned on.

The graph keeps exact original spans, neutral discourse relations, and relation nodes with ARG1/ARG2 edges (MEMBER for alternatives). CAUSE means event causation, CONSEQUENCE inferential result, JUSTIFICATION a reason offered for a claim, SUPPORT generic evidential support; CONDITION links antecedent to consequent. No NORMATIVE relation is used because it mixes proposition properties with discourse relations. Stanza dependency and constituency parsing guide segmentation; discourse edges are heuristic, not gold structure. In the roles engine, ambiguous connectives remain unresolved; the legacy engine optionally invokes its bounded pair resolver.

Primary extraction uses family-specific required attributes and distinct grounded defining roles. Short neutral role demonstrations come from train; their labels and IDs are omitted from prompts. Demonstrations from every evaluated article are excluded before --limit, including the whole validation partition. A criticized or reported argument is retained with its actual stance. Event endpoints exclude generic transition questions and discussion/advice clauses. Two alternatives differ from an open enumeration. Issue comparisons require independently extracted focal/comparison issues and a priority/downplaying claim; the code does not project ordinary actor-harm/function-loss/protection arguments into Worse Problems. The removed impact attribute does not affect inference. Legacy retrieval and verification remain available for comparison, but are not the default primary path.

Outputs:

- `report.html`: open locally, click a reason to inspect text, evidence, graph and verification; wrong predictions are highlighted.
- `results.jsonl`: one record per sample, shared by resume, metrics and report generation.
- `metrics.json`: accuracy, macro-F1, per-label metrics, candidate coverage and recovery count/rate. Full-selection accuracy counts unresolved samples and errors as unsuccessful; resolved-only metrics are separately identified.
- `manifest.json` and `cache.sqlite3`: internal resume identity and API response cache. Model/endpoint changes invalidate resume. A torn last result record is quarantined on resume.

No raw API dump, prompt dump, per-request audit file, separate graph directory or duplicated trace file is generated. Small runs show stage progress; large runs show counts every ten samples. Existing output is never silently overwritten. `--resume` skips resolved and unresolved records and retries API errors.

Compare methods with the same input, context and model:

```powershell
.venv/Scripts/python.exe -m scripts.discourse_classification --method direct --output baseline-direct
.venv/Scripts/python.exe -m scripts.discourse_classification --method rules --output baseline-rules
.venv/Scripts/python.exe -m scripts.discourse_classification --method graph --output graph-full
```

`direct` is one classification request. `rules` uses rule-based spans and the same role extraction/template matching and comparative verifier without Stanza. `graph` uses Stanza spans and heuristic discourse relations; the roles engine does not invoke implicit pair resolution. The initial cue lexicon and short-path motifs are baselines, not learned definitions or an exhaustive discourse parser. Use train/validation error analysis before freezing rules and evaluating the held-out classification test via `--split test --input PATH`.

Known limits: exact quote grounding validates location, not the semantic role assigned to a quote. Missing or incorrect role extraction can bias verification. Template ranking is auxiliary; a controlled verifier ablation is required before claiming graph contribution. Stance records criticism/reporting and is a tie-break rather than an absolute ownership gate. Keep `structured_output: false` with the current optional evidence-offset schema; strict provider schemas are not supported by this contract.

Small diagnostic results (2026-10-08, v3.1): four previously discussed examples produced one correct primary prediction and three unresolved outcomes; direct produced two correct predictions. Removing relations produced the same one correct prediction and three unresolved outcomes. Four dev examples were unresolved. Two train examples produced one resolved prediction and one unresolved outcome. These small runs do not establish an improvement or a graph contribution. The subsequent schema-validator correction rejects extra family fields and unknown kinds previously accepted by the local validator; pre-correction artifacts remain available for diagnosis and are not a final benchmark.

Historical schema-validated v3.2 rerun: the same four diagnostic examples remain 1/4 correct, 3 unresolved, 0 API errors and 0 recovery. The ALTERNATIVE bridge matcher now treats choice membership symmetrically; other relation paths remain directed. These changes repair implementation consistency, not demonstrated classification quality. Inspect `runs/classification-regression-v32/report.html`.

Historical diagnostic verification (2026-10-08, v4.5): regression_supported_three.json produced 3/3 gold-correct primary predictions, with grounded relevant evidence, no unresolved samples, no API errors, no recovery, and one extraction request per sample. The preceding v4.4 run also produced 3/3, with two extraction requests on one sample. The fresh code suite passed 253 tests. These are diagnostic results, not held-out benchmark scores or evidence that every role assignment is reliable.

Earlier v4.5 debugging permitted leaving 599:7794 unresolved instead of forcing a causal-to-comparison conversion. Under the v5.0 contract it must receive the closest eight-label prediction while retaining the original gold. Its original gold remains in regression_four.json. The separate supported-three subset excludes it transparently. A qualitative inspection of 12 randomly selected train Worse Problems comments from distinct articles found expressed focus/severity comparisons, unlike the diagnostic journalist-warning structure. This supports treating it as an atypical case; it does not establish annotation error.

A separate eight-sample article-disjoint train-validation smoke check on v4.3 produced 3/8 gold-correct predictions, 2 wrong predictions, 3 unresolved outcomes and 0 API errors. In particular, exact quote grounding did not prevent wrong SOURCE_JUSTIFICATION basis attributes. That run predates graph-driven coverage auditing; the eight-sample selection has not been rerun on v4.5. The three-sample success cannot establish general classification quality, and broad inference remains unverified.

To recheck the supported regression with the current code and a fresh output name (historical v4.5 reproduction requires its checkout):

```powershell
.venv/Scripts/python.exe -m scripts.discourse_classification --input data/cocolofa/classification/regression_supported_three.json --output classification-regression-check-v50
```
