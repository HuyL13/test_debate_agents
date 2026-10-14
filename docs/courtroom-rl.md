# Courtroom-MARL V1

This subsystem runs inside `cocolofa_pard`; it does not alter the existing
pipelines, data files or `.env`. Reuse/attribution: [courtroom-reuse.md](courtroom-reuse.md).
Design: [courtroom-design.md](courtroom-design.md).
Verified results and live pilot paths: [courtroom-validation.md](courtroom-validation.md).

## Environment

Use the existing `.venv` and install `requirements-courtroom.txt` when preparing
another environment. CPU PyTorch is sufficient. The existing `.env` supplies
`NVIDIA_API_KEY`, `NVIDIA_BASE_URL`, `NVIDIA_MODEL`. Tested model:
`openai/gpt-oss-20b`, endpoint `https://integrate.api.nvidia.com/v1`.
Never put credentials in YAML or command arguments.

Commands below run from `D:\Downloads\cocolofa_pard` in PowerShell. Use a new
output directory each time; runs are never overwritten.

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_courtroom_env.py tests/test_courtroom_ppo.py tests/test_courtroom_integration.py tests/test_courtroom_evidence.py -q
.\.venv\Scripts\python.exe -m src.courtroom_rl.runner audit --fixture --output runs/courtroom-audit
.\.venv\Scripts\python.exe scripts/smoke_courtroom.py --fixture --output runs/courtroom-fixture
.\.venv\Scripts\python.exe scripts/smoke_courtroom.py --output runs/courtroom-live
```

`--fixture` is deterministic plumbing verification, not a real model or accuracy
experiment. Smoke defaults to one **train** sample; evaluation defaults to dev.
The runner verifies hashes and official split membership of the approved flat
classification files: train 3168, dev 927, test 481. A pinned upstream loader
handles their schema; there is no second preprocessing pipeline. Gold lives only
in the runner/reward context, never public state, observation or model prompts.

## Pilot training and evaluation

```powershell
.\.venv\Scripts\python.exe -m src.courtroom_rl.runner train --fixture --limit 8 --dev-limit 4 --batch-size 4 --output runs/courtroom-train-fixture
.\.venv\Scripts\python.exe -m src.courtroom_rl.runner train --limit 8 --dev-limit 4 --batch-size 4 --output runs/courtroom-pilot
.\.venv\Scripts\python.exe -m src.courtroom_rl.runner evaluate --checkpoint runs/courtroom-pilot/best.pt --limit 16 --output runs/courtroom-learned-dev
.\.venv\Scripts\python.exe -m src.courtroom_rl.runner evaluate --policy fixed --limit 16 --output runs/courtroom-fixed-dev
.\.venv\Scripts\python.exe -m src.courtroom_rl.runner evaluate --policy single --limit 16 --output runs/courtroom-single-dev
.\.venv\Scripts\python.exe -m src.courtroom_rl.runner evaluate --policy heuristic --limit 16 --output runs/courtroom-heuristic-dev
.\.venv\Scripts\python.exe -m src.courtroom_rl.runner evaluate --policy random --limit 16 --output runs/courtroom-random-dev
```

Omit `--limit` to use the full official split. Train always uses train only and
shuffles its selection reproducibly by `--seed`; dev selection is fixed for
matched comparisons. `--epochs` controls complete passes. API training and
validation can be expensive: pilot first, inspect failures/coverage and actual
calls/tokens before increasing samples. No large API training is automatic.

The heuristic uses one frozen Prosecutor classification call as its initial
label/claim, challenges once, then selects the current charge with a code-only
verdict. This is a cheap comparison policy, not an independent Judge classifier.
The learned policy selects its own accusation and verdict labels. Its observations
include source text and per-claim original/challenge/response text as frozen
128-D word/bigram hashes plus lifecycle/budget features. These hashes are a
compact V1 approximation, not pretrained semantic embeddings or a full Markov
representation. Trainable type/target heads use fixed label and claim slots,
not a learned text encoder. Pretrained embeddings and pointer attention remain
separate extensions/ablations.

## Following RL training in the console

Training prints elapsed time and named stages by default:

```text
[00:00:04] [EPISODE] 1/8 epoch=1/1 sample=187:4758: rollout started
[00:00:04] [API] Prosecutor.ACCUSE target=Appeal to Tradition attempt=1: waiting for response
[00:00:34] [API] Prosecutor.ACCUSE target=Appeal to Tradition attempt=1: still waiting (30s)
[00:00:45] [EPISODE] 1/8 ... wrong reward=-1.051 decisions=5 calls=2 tokens=3560 stop=judge verdict elapsed=41.0s
[00:03:10] [PPO] update=1 actor_loss=... critic_loss=... entropy=... approx_kl=...; batch reward_mean=... acc=... forced=...
[00:04:20] [DEV] acc_success=... macro_f1=... coverage=... failed=... forced=...
[00:04:20] [CHECKPOINT] Saved .../last.pt; new best dev macro_f1=... -> .../best.pt
```

This is an illustrative layout, not a measured experiment. `[START]` shows model,
train/dev sizes, seed and budgets; `[BATCH]` shows rollout batch progress.
`[EPISODE]` summarizes correct/wrong outcome, total reward (including costs),
decisions/calls/tokens, stop reason and duration. Tokens including conservative
reservations are marked as estimates. Batch accuracy/reward refer only to valid
episodes in that batch, not held-out quality. `[DEV]` metrics refer to successful
dev predictions with explicit coverage; no valid predictions prints `n/a`.
`[ERROR]` identifies excluded cases and the existing failure artifact path.
`[DONE]` distinguishes attempted/completed/excluded episodes and PPO updates.

API waits emit a heartbeat every 30 seconds and identify the role/action/target
and attempt; attempts after the first are marked retry. A received response still
needs schema/evidence validation, so it is not labelled a valid output yet.
No source text, prompts, response bodies or credentials are printed.

For every role decision (including code-only rest/request/verdict), add:

```powershell
.\.venv\Scripts\python.exe -m src.courtroom_rl.runner train --limit 8 --dev-limit 4 --batch-size 4 --log-steps --output runs/courtroom-with-steps
```

`--log-steps` adds `[STEP] decision=... Role.ACTION target=...` in train and its
validation rollouts. It is console-only, adds no persisted logging artifacts and
does not change sampled actions or optimizer results. Fixture smoke verifies
progress/heartbeat/error cleanup without spending API calls.

## Resume and replay

```powershell
.\.venv\Scripts\python.exe -m src.courtroom_rl.runner train --limit 8 --dev-limit 4 --batch-size 4 --resume runs/courtroom-pilot/last.pt --output runs/courtroom-resumed
.\.venv\Scripts\python.exe -m src.courtroom_rl.runner replay --trace runs/courtroom-live/traces.jsonl
```

Resume requires the same training selection, seed, epoch target, configuration,
resolved model/endpoint and source code. Checkpoints contain actor/critic,
optimizer, RNG states, provenance and cursor. `last.pt` resumes after the last
completed batch boundary; an interruption during an API batch repeats that unfinished
batch. `best.pt` is selected by dev macro-F1 only when dev coverage is complete.
Use only trusted local `.pt` files. Frozen API model names may be provider aliases;
the runner freezes configured IDs/prompts/decoding, but cannot guarantee that a
provider never updates underlying weights behind an alias.

Replay uses saved action results and budget-failure events, makes no API calls,
and checks every legal-action mask and normalized state hash through verdict.

## Evidence ID contract (v2)

LLM outputs select `evidence_ids`; they no longer generate `supported_quote`,
source names or offsets. Supplied passages use `T1...` for target comment,
`P1...` for parent and `H1...` for title. Ordinary sentences retain their complete
text; exceptionally long sentences (>120 words) reuse the existing 30-word
passage splitter. Segmentation is deterministic and heuristic, not a linguistic
sentence parser. Source characters, whitespace inside passages and offsets are
preserved without normalization.

Code resolves one to three distinct IDs to `evidence_spans`, each containing
`id`, `source`, `start`, `end`, `quote`. Disjoint passages stay separate. The first
span also supplies the compatibility `supported_quote`/`source` fields. Ledger
validation re-derives allowed IDs and checks all fields, including repeated-text
offsets; replay uses the same checks. Novelty/dedup compare the whole evidence set.
Accusation/revision accepts target evidence only; defense/replies may use context.
NVIDIA does not support `uniqueItems` in its grammar, so duplicate IDs are rejected
by code rather than that schema keyword.

`--policy fixed` uses the same ID adapter for Prosecutor/Defender while retaining
the original three-stage routing and restored report schemas. Baseline reports
include a separate `evidence_resolutions` map for source/offset inspection. Use
`--policy fixed-original` for the unadapted upstream quote-generation baseline.
These are explicitly different execution contracts and must be identified in
comparisons. Judge verdict schema remains unchanged.

Prompt/cache version is `courtroom-evidence-ids-v2`; old free-quote cache entries
are not reused. Older checkpoints/source-version traces remain preserved but
cannot be resumed/replayed directly under the changed source contract. Start a
new training run for v2; the existing source-hash gate rejects silent mixing.

Accepted quotes are exact source extractions. This does not establish that the
selected passages are relevant, that the mechanism is correct or that the chosen
fallacy label is correct. Executors may explain that a selected label lacks
support; quote validation is not a correctness oracle.

## Budgets and outputs

`configs/courtroom_rl.yaml` sets decision/call/token caps and PPO/reward settings.
At most the configured number of ordinary decisions are followed by one forced,
code-only Judge verdict if necessary. This last decision is collected on-policy,
scored terminally and marked `forced_verdict`; it is not an unscored truncation.
Every attempted API call/rejected response consumes budget. Preflight uses a
conservative UTF-8 byte upper estimate (including output schema) and caps output
tokens; this may stop earlier than a provider-specific exact tokenizer would.
The fixed baseline has the same caps; if its three stages cannot complete, it is
reported as `budget_exhausted`, with coverage, rather than assigned a fake verdict.
If timeout/missing usage prevents exact accounting, token allowances are reserved
conservatively and `estimated_usage_calls` explicitly identifies estimates. Cache
entries preserve the effective usage and its estimate flag.

Exact duplicate claims under the same role/label/relation/evidence are rejected.
Frozen hashed-text cosine >= .90 flags similar claims under those same conditions
for inspection; it never rejects a claim on similarity alone. In particular,
negation and scope changes remain admissible. This is a lightweight review
signal, not a validated semantic equivalence detector.

Training uses fresh rollouts and disables response caching. Evaluation can enable
`--cache`, backed by `cache/courtroom_rl/responses.sqlite`. Cache keys include the
full public state/history, prompt/schema and model settings. Cached logical
calls/tokens still count toward inference caps; API audit distinguishes actual
provider calls. No raw request/response debug dump is enabled by this runner.

Each run contains public `run.json`, `summary.json`, evaluation predictions and
one `traces.jsonl` inspection/replay record per completed episode. Training adds
update summaries, checkpoints and failures only when failures occur. Existing
client `api_audit.jsonl` records physical attempts and validation errors. Gold
appears in evaluation predictions; rewards appear in training traces. Neither
artifact is supplied to LLM agents or policy encoders.

`summary.json` reports accuracy/macro-F1/per-label F1/confusion on successful
predictions, explicit coverage/failure counts, correct-over-attempted, and
mean/median/p90 calls/tokens/decisions plus forced-verdict rate. Failed samples
are preserved and never silently discarded. Repeated seeds, uncertainty
intervals, concede audits, shaping and IPPO comparisons are research experiments
to run after validating this V1; fixture and small pilots cannot establish a
performance improvement.

## Data audit findings

No article-ID overlap was found across official splits. One normalized identical
comment crosses train/dev: `641:9119` and `13:9337`; the audit records it without
altering official membership. No cross-split near-duplicate candidates were
found for train/test or dev/test at hashed character 3–5gram cosine >= .95.

Raw `test.json` differs in byte checksum from provenance, but its parsed JSON is
identical to the exact pinned upstream Git object at
`c39d45fdd57401e1f6cb674f25113dfa0304e734`. The flat classification test also
matches both its recorded checksum and current raw-loader output. Original files
are preserved.
# Reward revision: CREW component deltas

Both default and pilot configurations now use section 8.2B (`reward.mode: crew`).
At step t, w ramps from .2 to .8 over the configured decision horizon. Progress
is `(1-w)*(.4*delta_local+.6*delta_board)+w*delta_decision`; reward adds
`.3*clip(progress,-1,1)`, terminal +/-1 once, step cost .01, generated-token cost
1e-5 and invalid-action cost .1. Components use bounded [0,1] scales. Unique
source evidence and per-role contributions persist; repeated actions do not earn
quality-level bonuses. Wrong-class charges cannot earn positive decision gains.
An additional absolute shaping budget of .5 per episode bounds surrogate influence.

Local and board quality are class/status/evidence consistency proxies, not logical
proof. The frozen TF-IDF/logistic assessor reads original input and unique source
excerpts, never generated rhetoric or proposed labels. It is fitted on official
train with an article-grouped 20% train calibration partition. It uses the full
train split even when RL `--limit` is smaller. Gold probability and reward scores
remain private to the reward engine and trace diagnostics; they are absent from
actor/critic observations and LLM prompts. Dev/evaluate disable dense shaping.
The classifier is a pragmatic proxy, not an LLM judge of argument correctness.

Offline preparation and comparisons (PowerShell, repository root):

```powershell
.venv\Scripts\python.exe -m src.courtroom_rl.runner prepare-assessor
.venv\Scripts\python.exe -m src.courtroom_rl.runner evaluate --policy assessor --split dev
.venv\Scripts\python.exe -m src.courtroom_rl.runner train --fixture --limit 8 --dev-limit 2 --reward-mode crew
```

`--reward-mode terminal` retains 8.1; `--reward-mode potential` uses 8.2A with
alpha=.25, bounded log q_gold, terminal potential zero and PPO-matched gamma.
Only potential shaping has the telescoping property; CREW shaping is experimental
and has no policy-invariance guarantee. Assessor hashes are checked on resume.
Use a new artifact path when changing assessor settings/data. Load only trusted
local joblib artifacts. These commands do not repair the separately paused model
response compatibility work; fixture verification makes no live API calls.

# Current default: action-centric V3

The default/pilot CLI now runs action-only role actors. LLMs choose all labels
and claim/hypothesis targets, including the Judge verdict. See
[V3 usage and migration](action-centric-v3.md) for current commands, budgets,
warmup, metrics and checkpoint requirements. The sections below document earlier
label-selecting V2 experiments and the reward groundwork; use the legacy config
to reproduce that controller architecture.

