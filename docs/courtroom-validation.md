# Courtroom validation — 2026-10-13

## Evidence-ID v2 update

- Full repository suite: **313 passed** (269 pre-existing, 44 courtroom).
- Independent review findings on full evidence identity and replay ID validation
  were reproduced, fixed and re-reviewed with no further material findings.
- Real NVIDIA calls on the previously failing train sample `187:4758`:
  `ACCUSE(Appeal to Tradition)` and `CHALLENGE(C1)` both selected `T4`.
  All resolved quotes and offsets matched their original source exactly.
- New live trace replay passed without any API calls.
- Live artifacts: `runs/courtroom-evidence-ids-verified-20261013/`.
- An initial request revealed NVIDIA rejects schema `uniqueItems`; this keyword
  was removed, while duplicate rejection remains enforced in code.

This validates the evidence extraction contract, not label/reasoning accuracy or
provider stability. No v2 PPO retraining or classification-quality claim is made.
V1 checkpoint artifacts below are historical and do not pass the current v2
source-hash gate; they have not been overwritten or relabelled as v2 models.

## Historical V1 validation

- Full repository suite: **303 passed** (269 pre-existing, 34 courtroom).
- Independent code review: material findings fixed and regression tested.
- NVIDIA action executor: real structured responses validated against source quotes.
- Final-source live PPO pilot: **1 completed train episode, 1 update, 1 dev episode**,
  no excluded episodes in that run; checkpoint source hash matched that V1 source.
- Real trace replay: matching legal masks, normalized states and verdict.
- Resume from final `last.pt`: completed successfully, with no repeated API calls
  because the selected one-episode training run was already complete.
- Gold/privacy, masks, irregular-turn GAE, retry/cache accounting, budget forcing,
  malformed grounding, lifecycle, save/load and replay have targeted regressions.

Final live artifacts: `runs/courtroom-verified-seed1-20261013/` (ignored by Git).
Config: `configs/courtroom_rl.pilot.yaml`; seed 1, one train and one dev sample,
four ordinary decisions and two calls per episode. `best.pt`/`last.pt` are
plumbing-pilot checkpoints, not production models. Dev macro-F1 was 0 on the one
sample; no accuracy improvement is established.

```powershell
.\.venv\Scripts\python.exe -m src.courtroom_rl.runner replay --trace runs/courtroom-verified-seed1-20261013/traces.jsonl
.\.venv\Scripts\python.exe -m src.courtroom_rl.runner train --config configs/courtroom_rl.pilot.yaml --limit 1 --dev-limit 1 --batch-size 1 --seed 1 --resume runs/courtroom-verified-seed1-20261013/last.pt --output runs/courtroom-resume-check
```

Provider limitations observed: variable latency, 120-second timeouts and
occasionally non-verbatim generated quotes. Responses remain strictly checked;
bad outputs retry finitely and become explicit failures, never valid predictions.
Unknown token usage after timeout is reserved conservatively and marked as
estimated. The final live pilot had such a timeout, then a valid retry.

The real fixed baseline smoke did not complete: timeout followed by a rejected
quote under its original validator. Its three-stage execution is covered by
fixture regression, and the failed live attempt is retained at
`runs/courtroom-fixed-live-20261013/`; no successful real baseline score is claimed.

Data audit: flat counts/hashes/contexts verified; no article overlap, one identical
train/dev comment pair recorded. Parsed raw JSON matches the pinned upstream
commit for all three splits, including test despite its differing byte checksum.

Not run: full 3168-example API training, full dev/test evaluation, repeated-seed
statistical experiments or quality ablations. Optional shaping, pretrained claim
embeddings/pointer attention and IPPO remain follow-up research extensions.
# Resume and fallacy logging verification (2026-10-14)

Final regression: **376 passed**. Four new tests cover extending total epochs,
skipping completed warmup, inheriting best.pt, preserving parent provenance,
rejecting epoch shrinkage/unknown source migrations and displaying actual labels
without LLM-selected placeholders. At matching batch boundaries, fixture split
training matches uninterrupted policy/critic weights, Adam moments and Torch RNG.

Offline preflight of `courtroom-v3-20261013T145658230132/last.pt` restored cursor136,
135 scored episodes and17 updates; all config/data/model/assessor/tokenizer
contracts passed and a total target of2 epochs was accepted. No API requests or
optimizer steps were made. The original checkpoint was not modified. Exact source
migration is registered in diagnostics/resume-source-migrations.json; no generic
source-check bypass was introduced. Review found no critical issue.

# V3 reliability fixes verification (2026-10-13)

Final full regression: **372 passed** (including10 targeted reliability tests).

Known pilot failures: byte admission rejected SUPPORT/CHALLENGE with ample real
token budget; JSON-object prompts included raw schemas that the model copied;
alternative no-ops had no valid null-label representation. Fixed with optional
pinned BPE input estimates + margin, strict usage-overrun audit, V3 result guides,
targeted retries, strict whole-result envelope decoding and conditional no-op
validation. Shared legacy parser defaults remain strict. Actor/reward design unchanged.

`runs/v3-reliability-final-live`: four known problematic train cases completed,
including two PROPOSE_ALTERNATIVE executions and two full CHALLENGE/request/SUPPORT
paths.15 provider attempts, one evidence-count response rejected and retried;
no forced verdicts, no admission rejections or usage overruns. Tokens per case:
9044,6043,9156,9459, each under unchanged24000-token/8-call caps. Admission
estimates exceeded provider-reported prompt tokens by316–388 across these requests.
All four verdicts matched gold, but this deliberately selected diagnostic sample
does not estimate accuracy or establish full-dataset reliability. No optimizer
updates or old-checkpoint contract bypass were used in the live audit.

All four final live traces replay with matching states/verdicts. Fixture training
in `runs/v3-reliability-fixture` completed4/4 episodes, warmup2, PPO updates2, dev8/8.
Independent review found nested Top3 placeholder and structured-schema-count gaps;
both corrected with regressions. The accidentally broad placeholder check that
rejected mathematical arrows was also corrected. Final review found no critical
issue. Decoder/source/config changes require a new training run, not resume from
the prior pilot checkpoint.

# Action-centric V3 verification (2026-10-13)

Final full regression: **362 passed**, including26 V3 contract tests. Covers
Top3 distinctness/grounding/retries, action-only actors, LLM-selected target C2,
all8 verdict outside Top3, per-role parameter updates, gold/public-stat isolation,
atomic duplicate/invalid rejection and tighter eligibility, generated-token costs
across all reward ablations, cached-budget enforcement, forced paid verdict,
partial-failure traces, global-time PPO and checkpoint batching contracts.

`runs/action-centric-final-check`: four fixture train episodes, two warmup action
demonstrations, two PPO updates; role decisions P2/D6/J8, dev8/8 completed.
Checkpoint saved and resumed under the same contract. All four episode replays
match state/verdict hashes. Fixture metrics do not measure model quality.

`runs/action-centric-final-live`: one real Llama fixed-Top3 episode completed in
three calls /5935 tokens, all outputs valid on first attempt. Initial Top3 was
distinct and grounded; Defender LLM chose a target; Judge LLM chose Appeal to
Authority, matching this case's gold. Final live trace replay also matches.
Earlier two-claim smoke produced malformed JSON; final default limits init to
one claim per hypothesis (two remains configurable), and uses adapted original
role behavior with single action schemas. This small smoke does not establish
reliability or accuracy over the dataset, and no full V3 RL experiment was run.

Independent review: fixed role-behavior reuse and loss of partial failed traces;
follow-up found and fixed unnecessary dev sweeps after failed batches and missing
batch-size resume checks. No critical issue remained in that review. V2 and earlier
intermediate V3 traces/checkpoints may fail current source/state contracts;
verification does not bypass these checks. Current usage: action-centric-v3.md.

# CREW reward revision verification (2026-10-13)

RL action prompt fix: old classification role prompts required baseline report
fields alongside the RL action schema, causing ACCUSE failures on samples
187:4758 and 77:3678. RL now reuses common grounding and fallacy definitions but
has its own single action contract with concrete schema/example. Strict JSON,
label and evidence validation remain enabled; no alias mapping or field dropping.
Prompt version is courtroom-single-action-v3. Regression suite: 336 passed,
including three new prompt-contract cases. Existing checkpoints have a different
source hash and require a new run rather than resume across this change.

Model switch (2026-10-13): `.env` now selects
`meta/llama-3.2-11b-vision-instruct` at NVIDIA with the key from `key.txt`.
Direct request returned HTTP 200. Strict-schema smoke failed because the model
returned legacy extra fields; both courtroom configs now use JSON-object mode
with schema included in the prompt, and omit reasoning_effort. Live smoke in
`runs/llama-vision-json-smoke` completed 1/1 case with validated outputs, including
a retry for extraneous JSON text. Classification was wrong on that case; this
verifies API integration only, not model accuracy or training stability.
Targeted LLM/integration regression: 23 passed. No reward changes in this switch.

CPU assessor fitted/calibrated on grouped official train only; artifact fingerprint
recorded in training checkpoint metadata. No live model API calls in this revision.
Final regression suite: 333 passed (project virtual environment).
Fixture train: 2/2 episodes, one PPO update, checkpoint saved; state replay matched
both episodes. Source-only assessor baseline evaluated 16 dev cases without API
calls (small wiring check, not a representative performance estimate).
Reward regressions cover private gold/score separation, component mixing, terminal
once, generated-token cost, wrong-charge gain suppression, negative decision delta,
no-op/repeat/subset evidence behavior, bounded shaping and potential telescoping.
Independent review found evidence-combination reward farming; fixed by atomic
source-span deduplication for local and board units. Proxy semantics and paused
model compatibility are documented in courtroom-rl.md.

