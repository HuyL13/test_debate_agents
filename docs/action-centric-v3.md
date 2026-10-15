# Action-centric courtroom V3

The default and pilot configs select `architecture: action_centric_v3`.
Specification: [courtroom-action-centric-design.md](courtroom-action-centric-design.md).
This replaces label-selecting RL with strategic action selection. Existing V2
modules and fixed one-pass baseline remain available for comparison; V2 checkpoints
cannot initialize V3 actors.

## Responsibility and episode

| Role | Actor outputs | Frozen Llama outputs |
| --- | --- | --- |
| Prosecutor | SUPPORT, REVISE, REST | Hypothesis/claim, label if revising, grounded explanation |
| Defender | CHALLENGE, PROPOSE_ALTERNATIVE, CONCEDE, REST | Target claim, justified alternative label, critique/concession |
| Judge | REQUEST_SUPPORT, REQUEST_REBUTTAL, VERDICT | Final label among all8, grounded rationale |

Top3 initialization is a paid Prosecutor LLM call, outside the PPO timeline. It
must return three distinct valid labels with source-grounded claims. Default is
one claim per hypothesis to reduce JSON complexity; set budget
`max_initial_claims_per_hypothesis: 2` to allow two. Ledger capacity defaults to8,
hypothesis capacity8, and at most10 RL decisions including forced verdict.

Initial control goes to Defender. Judge requests route to the requested **actor**;
they do not call a pre-action Judge/proposer LLM. Pending request describes eligible
scope; the subsequent role LLM chooses the exact issue/claim. A Judge VERDICT
action invokes Judge LLM; neither action logits nor policy rows contain label or
claim-ID decisions. Final label is not restricted to Top3 or current hypotheses.

## Public features and learning

CREW Actor/Critic MLPs are reused as three separate action actors and three local
critics. P/J observations have29 dimensions, D36: six features per action, one
past-statistic validity flag per action and eight shared global features. Features
are bounded relevance/opportunity/evidence-gap/novelty/past structural impact/cost.
No private reward/gold statistics enter these rows. Unobserved EMA=.5 with validity0.
`--observation-mode semantic` uses pinned frozen BGE-base-en-v1.5 embeddings and
cosine relevance. This is semantic similarity, not a proof of valid reasoning.

PPO computes GAE on the complete global event timeline before role-wise advantage
normalization; gaps between a role's decisions are not collapsed. Actors select
masked action categories only. Model weights remain frozen. Optional warmup
imitates train-only heuristic **actions**, not labels, and is not fed to PPO as
on-policy data. It consumes additional API calls recorded in warmup traces.
Per-batch and cumulative role decision counts expose missing Prosecutor coverage.

## Validation, reward and budgets

Exact evidence IDs/offsets reuse the existing resolver. Updates are transactional;
invalid targets/duplicate content leave hypotheses and claims unchanged, incur
costs and tighten subsequent eligibility. Similarity only flags possible duplicates.
No-op alternatives add no hypothesis, gain no quality and pay the invalid/no-op
penalty. Public statuses describe dialogue positions, not gold correctness.

Reward reuses bounded private CREW component deltas. Local/board quality are
grounded class/kind/status consistency proxies, not proof of valid reasoning. A
frozen train-only source classifier supplies private bounded log-q_gold changes.
It fits/calibrates using the full official train even when RL `--limit` is smaller;
report that supervised data budget when comparing experiments.
Wrong-label SUPPORT/REVISE/alternative arguments cannot receive positive decision
gain. Absolute shaping remains capped at.5 per episode. Terminal-only and potential
ablations are available. Main, pilot and Kaggle configs charge .01 per decision
and .00001 per generated token; call cost remains zero. Hard episode budgets
and invalid/no-op penalties remain. PPO gamma remains .99. Reward changes require
a new training run; strict resume rejects checkpoints with different reward
configurations. An already running process keeps the configuration it loaded
at startup.
Potential shaping retains its gamma/telescoping rule, whereas CREW
shaping has no policy-invariance guarantee. Dev evaluation disables dense shaping.

Initialization call/tokens count toward inference budgets and reporting, but no
initialization actor transition/bonus is invented. PPO returns begin after init;
the frozen initialization's costs are outside those actor returns. One call and
8000 tokens are reserved for the final verdict. Default V3 admission uses a pinned
Llama3-compatible BPE counter with framing/margin, replacing the byte bound that
prematurely blocked SUPPORT. Actual provider usage remains authoritative; overruns
are accounted and rejected. The original byte fallback remains for other configs
without a tokenizer. Forced verdict is
an actual paid LLM call, not an actor-selected label or free unlimited retry. An
unavailable/timed-out/malformed final response remains a reported infrastructure
failure. A reserve does not guarantee provider success on every input.

The9MB tokenizer is already prepared at `cache/courtroom_rl/llama3_tokenizer.json`.
Its SHA256 and immutable NVIDIA source URL are pinned under `tokenizer` in both
configs; live runs fail clearly on missing/tampered artifacts or model-family
mismatch. To restore the artifact in a new checkout, create `cache/courtroom_rl`
and download that exact config source to that path; the loader verifies its hash.
This is a compatible text estimator, not a claim of exact vision-server token
counting. All V3 baselines use the same estimator and unchanged inference caps.

JSON-object requests now supply result templates and explicit eligible labels/IDs,
not a full schema in the model prompt. Local schema/grounding validation stays on.
Retries show the previous rejected output and action-specific corrective rules.
A whole-response JSON fence or a singleton `output_example` envelope can be decoded
without changing its contents; sibling fields, extra inner fields, multiple objects,
placeholders and invalid semantic choices remain rejected. Normalization is audited.
An alternative no-op requires `label=null`, `no_op=true`, `evidence_ids=[]` and a
reason; it never invents a label or adds a hypothesis. V3 decoding now uses
temperature0 and up to3 attempts, still bounded by episode call/token budgets.

Terminal logs print `[INIT]` Top3, `[RESULT]` LLM-selected target/label, `[VERDICT]`
actual prediction and `[BUDGET]` estimated input/output/remaining allowances.
Episode summaries print prediction and gold only after the rollout; gold stays
out of actor inputs and LLM prompts.

The API audit retains all attempts. `partial_traces.jsonl` preserves unfinished
episodes and their failure stage; they are explicitly excluded from PPO, never
converted to fabricated predictions. Evaluation reports coverage and accuracy
over attempted samples alongside successful-prediction metrics. Top3 recall
includes every validated initialization, even when its later verdict fails.

## Commands (PowerShell, repository root)

Offline verification:

```powershell
.venv\Scripts\python.exe -m src.courtroom_rl.runner train --fixture --limit 8 --batch-size 4 --dev-limit 8 --warmup-episodes 2 --log-steps
```

Small live training pilot (uses the existing Llama key/model):

```powershell
.venv\Scripts\python.exe -m src.courtroom_rl.runner train --limit 32 --epochs 1 --batch-size 8 --dev-limit 16 --dev-every 4 --warmup-episodes 8 --seed 0 --log-steps
```

Remove `--limit 32` for the entire official train split. Warmup is optional and
defaults to0; monitor per-role coverage if omitting it. Dev subset is fixed and
stratified across all8 classes when `--dev-limit >= 8`. Validation occurs every
four successful PPO updates by default and at the final batch, avoiding a paid
dev sweep after every failed batch.

Baselines and ablations:

```powershell
.venv\Scripts\python.exe -m src.courtroom_rl.runner evaluate --policy fixed-top3 --split dev --limit 16
.venv\Scripts\python.exe -m src.courtroom_rl.runner evaluate --policy fixed-original --split dev --limit 16
.venv\Scripts\python.exe -m src.courtroom_rl.runner evaluate --policy random --split dev --limit 16
.venv\Scripts\python.exe -m src.courtroom_rl.runner evaluate --policy heuristic --split dev --limit 16
.venv\Scripts\python.exe -m src.courtroom_rl.runner train --limit 32 --reward-mode terminal
.venv\Scripts\python.exe -m src.courtroom_rl.runner train --limit 32 --reward-mode potential
```

Use identical model, decoding, sample selection and call/token budgets for fair
quality/cost comparisons. `fixed-top3` follows init -> challenge -> verdict; fixed
single-charge baseline retains original flow and schema through the existing adapter.
Do not infer quality from fixture results or from a single real smoke case.

Resume requires the same configuration, seed, selection, batch size,
warmup setting and dev interval; add `--resume <run>/last.pt` with those original
arguments and a new output directory. `--epochs` is the total target epoch count:
it may stay the same to finish an interrupted run or increase to train further;
it cannot shrink. Resume restores actor/critic, Adam optimizer and RNG states,
continues from the saved batch cursor and automatically skips completed warmup.
Keep the original `--warmup-episodes` value for contract verification; it does not
repeat those demonstrations. Compatible best.pt is inherited, with resume.json
and checkpoint history preserving the parent provenance. Exact split/uninterrupted
equivalence is verified when the split follows the same PPO batch boundaries;
an already applied partial final batch cannot be undone when extending epochs.
Completed batch checkpoints save actor/critic,
optimizer/RNG, data provenance, assessor hash and model/source/config contracts.
Use `--checkpoint <run>/best.pt` for frozen learned-policy evaluation. Replay accepts
V3 initialization plus trace and does not require gold or an assessor:

```powershell
.venv\Scripts\python.exe -m src.courtroom_rl.runner replay --trace <run>/traces.jsonl
```

Preserved legacy control is selected by `--config configs/courtroom_rl.legacy.yaml`.
Legacy checkpoints from before these source changes fail the source-hash contract;
do not bypass that check. A reviewed exact from/to source-hash migration in
`docs/diagnostics/resume-source-migrations.json` allows the existing reliability-V3
checkpoint to resume after the console-log/resume-lifecycle update. This is not
a general ignore-source flag; future unregistered changes still fail verification.
Stop an old training process yourself before starting a
replacement run; this migration does not kill existing processes.

Continue the interrupted full-train run from its latest saved batch:

```powershell
.venv\Scripts\python.exe -m src.courtroom_rl.runner train --resume runs/courtroom-v3-20261013T145658230132/last.pt --epochs 1 --batch-size 8 --dev-limit 66 --dev-every 10 --warmup-episodes 8 --seed 0 --log-steps
```

Use `--epochs 2` instead to target two epochs in total, including the work already
completed. Pre-request STEP/API logs show the chosen strategy without a made-up
label. Actual results show `fallacy=Appeal to Authority` or
`[VERDICT] prediction=Slippery Slope`; initialization prints all three real labels,
and train/dev summaries print prediction and gold only outside model inputs.


## Frozen semantic encoder

Semantic observations now use BAAI/bge-base-en-v1.5 (BERT, 768 dimensions), pinned
at a5beb1e3e68b9ab74eb54cfd186867f64f240e1a, via transformers AutoModel.
The main/pilot encoder runs on CPU; Kaggle runs it on cuda alongside PPO.
The encoder is frozen/eval/inference-only, outside the PPO optimizer. Public title,
parent comment and comment are compared to each eligible claim proposition using
normalized CLS cosine; maximum relevance supplies the existing scalar action-row
feature. Actor input dimensions stay unchanged: the full768-vector is not concatenated.
Texts longer than512 tokens are split into overlapping chunks (64-token overlap),
normalized CLS vectors are averaged and normalized again. An LRU4096-text cache
avoids redundant inference. No gold labels, private scorer output or reward enters
encoder input. No retrieval query instruction is used for this symmetric comparison.
There is no hash fallback in real training: loading failures stop before paid calls.
Offline --fixture explicitly uses a separate synthetic hash encoder.
Weights download from Hugging Face on first use (about440MB); subsequent runs reuse
its cache. BGE is a practical English/T4 choice, not a measured best model on this task.
Changing encoder/observation requires fresh training; older checkpoints are incompatible.

Development set update (2026-10-15): new main/pilot/Kaggle runs default to all66 pinned dialectical diagnostic cases, originally selected from official test errors. Official train/dev/test artifacts stay unchanged. This development use exposes these test cases; do not report them as fresh held-out test. An explicit --dev-limit still subsets the configured development set. Older checkpoints have different source/config/dev-selection contracts and do not resume directly.
