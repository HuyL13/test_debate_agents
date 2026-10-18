# Reviewed fallacy graph method

Experimental graph pipeline: source-anchored propositions, directed relations,
warrant slots, reviewed TRAIN admission, witnessed pattern prototypes per label,
candidate matching and selective LLM verification. The method requires review
before graph admission to the pattern bank. Valid JSON is not semantic accuracy.

## Architecture

`stability/ontology_v2.py` defines literal spans, propositions, commitment and
inference applications. `decomposed_source_v2.py` extracts propositions and then
relations over fixed IDs. `warrant_slots_v2.py` adds constrained scheme roles;
adoption/concession typing is owned by code. Validators preserve original source
anchors, direction, endpoint constraints and rejected attempts.

`reviewed_training_v2.py` admits only reviews bound to the exact graph snapshot,
covering relations, central coverage, speaker/stance, negation/modality and roles.
Human review is the default; explicit assistant silver is a research tier.
`patterns_v2.py` mines alternative witnessed prototypes, with distinct-article
support, competing-label purity and bootstrap recovery. It never merges separate
examples into an unwitnessed path. `verify_v2.py` and `final_selection_v2.py`
separate selective classification from confirmed author-fallacy detection.

See [method decision](stability/FINAL_METHOD_DECISION.md),
[annotation guide](stability/RELATION_ANNOTATION_GUIDE.md),
[paper survey](stability/PAPER_SURVEY.md) and
[Market output workaround](stability/MARKET_REPAIR.md).
Historical diagnostic modules are retained for comparison; the supported
full-TRAIN extraction entry point below uses an explicit manifest. Older
`pipeline.dataset()` experiments require local historical `run-live/samples.json`
and are not the full-TRAIN workflow.

## Setup and full TRAIN extraction (PowerShell)

Run from `graph_method/stability` in the cloned repository. Python 3.11 is used.
Place the licensed dataset at the repository's
`data/cocolofa/classification/train.json`. Set credentials in the repository-root
`.env` using the variable names in `../.env.example`, or set environment variables.
`GRAPH_REPO_ROOT` optionally selects another data/credential root.

```powershell
python -m venv .venv-syntax
.\.venv-syntax\Scripts\python.exe -m pip install -r requirements-syntax.txt
.\.venv-syntax\Scripts\python.exe prepare_full_train.py
powershell -NoProfile -ExecutionPolicy Bypass -File .\run_market_train.ps1 -Name full_train_market_gptoss120b_r1
```

The launcher uses Market `gpt-oss-120b`, four workers and `prompt_json`:
the schema goes into the prompt rather than provider-native constrained decoding.
Requests are cached by input/prompt/configuration; rejected outputs remain visible.
The rolling failure guard stops queued work if fewer than 80% of the latest
32 completed graphs meet source contracts. This is an operational guard, not a
semantic accuracy gate. The same run name is protected by an exclusive lock.

```powershell
Get-Content .\full_train_market_gptoss120b_r1.log -Tail 20 -Wait
```

Outputs include graphs, stage metrics, raw calls and an HTML report. These remain
local and are ignored by Git. The full manifest uses TRAIN only, with all rows
marked induction; it provides no independent validation split.

## Reviewed pattern bank

Provide an approvals JSON list. Each entry needs `sample_id`, `graph_sha256`
(from `reviewed_training_v2.graph_fingerprint`), a named `reviewer`,
`reviewer_type: "human"` and all five `checks` set to true:
`source_relations`, `central_coverage`, `speaker_stance`, `negation_modality`,
`warrant_roles`. Do not synthesize approvals from class labels or model agreement.

```powershell
.\.venv-syntax\Scripts\python.exe reviewed_training_v2.py full_train_market_gptoss120b_r1_graphs.json approvals.json --output reviewed_pattern_bank.json
```

The bank reports missing supported labels; an extraction run does not imply a
ready bank. No expert approvals or eight-label-ready bank are shipped.

## Verification and observed limits

```powershell
.\.venv-syntax\Scripts\python.exe -m unittest discover -s . -p "test_*.py"
```

Small TRAIN regression fixtures are included; bulk training data, API caches,
credentials and generated reports are excluded. Tests run without API calls.
The Market 100-case diagnostic finished 100/100 requests with 99 graphs meeting
the final contracts: propositions 100/100, relations 100/100, warrant 99/100.
One warrant was rejected for binding its claim to the wrong target. No request
hit the output-token limit. This measures output contracts, not semantic accuracy:
manual inspection still found an evaluative phrase treated as a causal outcome.
The selected method therefore retains reviewed TRAIN admission and abstention.
