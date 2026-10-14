# Courtroom-MARL: Technical Design Specification

**Status:** Proposed design, not implemented or experimentally validated  
**Task:** Eight-class fallacy classification (every evaluated sample is fallacious)  
**Dataset:** CoCoLoFa, exact upstream splits and provenance used by `HuyL13/test_debate_agents`  
**Architecture:** Frozen LLM agents + trainable role-specific RL controllers + turn-based courtroom environment  
**Date:** 2026-10-13

## 1. Objective and scope

Build an RL controller that learns **which argument to challenge, when to revise a charge, when to concede, and when the judge should stop**. Do **not** optimize for prosecutor versus defense wins. All three roles cooperate at the *task* level to maximize gold-label classification accuracy while minimizing unnecessary calls and repeated argumentation; their dialogue *behavior* is adversarial.

Primary question: under matched model, data, and inference budget, does a learned dialogue policy improve accuracy/macro-F1 or reduce calls/tokens versus the existing fixed Prosecutor → Defender → DialecticalArbiter pipeline?

Non-goals for V1: fallacy detection (Non-Fallacious), LLM fine-tuning, changing the three role identities, generating new claims unrelated to source text, learning gold labels from test results, graph pattern induction, and additional LLM agents.

## 2. Source repositories: what is reused and what is changed

### 2.1 Existing courtroom baseline

Source: https://github.com/HuyL13/test_debate_agents/tree/feat/adversarial-dialectical-debate

- `src/adversarial_debate.py`: classification calls `Prosecutor` indictment → `Defender` plea → `DialecticalArbiter` verdict; defense may set `concede_charge` and an alternative class. This is **one-pass**, not trained RL.
- `src/adversarial_prompts.py`: role prompts and boundary/charity/concession instructions. Preserve their intent but adapt prompts for action-specific execution; avoid showing gold.
- `src/data/loader.py`: `Sample`, `ModelInput`, `load_split`, `select_task` and context handling.
- `scripts/prepare_data.py`: exact pinned CoCoLoFa blobs (`train.json`, `dev.json`, `test.json`) from commit `c39d45fdd57401e1f6cb674f25113dfa0304e734`; reproducible provenance.
- The adversarial experiment config `configs/classification.adversarial.nvidia.yaml` currently targets `data/dev_classification_errors`: **do not use this error-conditioned subset as the normal RL training distribution**. Use `data/cocolofa` classification positives from train.

### 2.2 CREW inspiration

Source: https://github.com/YenPBao/CREW-Collaborative-MARL

- `src/rl_env/rwg_env.py`: `reset`, per-agent `get_obs`, action dispatch, workspace transitions, step rewards, fixed horizon; uses `ThreadPoolExecutor` for simultaneous agents.
- `src/train_self_supervised.py`: shared-policy IPPO; per-paper episode, actor/critic selection, buffer collection, PPO update and checkpointing.
- `src/training/ippo_trainer.py`: per-agent rollout data and backward GAE.
- `src/networks/actor.py`: small categorical MLP policy.

**Retain**: a distinct RL action-selection stage; frozen LLM action execution; structured workspace; PPO/GAE; checkpoint/replay and instrumentation.  
**Replace**: simultaneous actions → sequential event-driven turns; interchangeable shared actor → role-specific actors; fixed-length episode → natural termination with a capped horizon; action-only categorical → hierarchical action + target masking; state similarity reward at every step → one terminal classification reward plus explicit costs, optionally policy-invariant shaping.

CREW's trainer stores `similarity(current_draft, gold_draft) + 0.1 * env_reward` at each step; do not copy this repeated level-based reward for Courtroom.

### 2.3 Mandatory implementation principle: maximize reuse from BOTH repositories

**HARD REQUIREMENT FOR CODEX/IMPLEMENTERS: Reuse existing, working code from both `YenPBao/CREW-Collaborative-MARL` and `HuyL13/test_debate_agents` wherever technically feasible. Do not rewrite a module merely to conform to a preferred new architecture.** The final system should be a narrow integration/adaptation layer around these codebases, not a third implementation of functionality they already provide.

Follow this order for each feature: **(1) locate an existing implementation in either repo → (2) reuse it unchanged if contracts fit → (3) wrap or subclass it if only the interface differs → (4) minimally refactor with tests → (5) implement from scratch only when neither codebase supports the requirement.** For each new module, document the specific reason reuse was insufficient. Keep attribution to original code, licenses and upstream commit SHAs.

**Prefer `test_debate_agents` as the owner of dataset and LLM-facing functionality:**

- Reuse `src/data/loader.py`, `scripts/prepare_data.py`, dataset validation/provenance, official train/dev/test handling and `ModelInput`; do not reimplement CoCoLoFa preprocessing, parent-comment lookup, or label mapping.
- Reuse the existing API transport, retries, caching, structured schemas/validators, logging, tracing and evaluation infrastructure **after inspecting their actual contracts**. Extend schemas only for action-specific claim/rebuttal payloads; do not duplicate API clients or create parallel evaluation code without need.
- Reuse `src/adversarial_prompts.py` and `src/adversarial_debate.py` role prompts/execution logic where possible. Preserve Prosecutor/Defender/DialecticalArbiter semantics and existing fixed pipeline as the no-RL baseline. Refactor existing one-pass calls into individually callable action executors rather than rebuilding prompts from scratch.

**Prefer CREW as the owner of RL machinery:**

- Reuse/adapt `src/networks/actor.py` and `src/networks/critic.py` for small trainable policies/value functions; add role-specific heads and legal action/target masks instead of replacing PyTorch PPO with a novel trainer.
- Reuse/adapt `src/training/ippo_trainer.py` buffer and GAE code **only after fixing turn-based irregular action intervals and terminal/truncation semantics**; retain PPO clipping, advantage normalization, checkpointing, diagnostics and stable optimization details from `src/train_self_supervised.py` when suitable.
- Reuse the environment interface and reset/step/observation/reward accounting patterns from `src/rl_env/rwg_env.py`, **not** its parallel action dispatch, shared 4-action semantics, 20-D hard-coded observation or per-step draft-similarity reward. Wrap as a turn-based `CourtroomEnv` compatible with chosen RL interface.

**Integration checklist (required before implementing a replacement):**

1. Produce a file/function-level reuse inventory mapping each feature to its existing source path and whether it is `reuse`, `wrap`, `minimal modification`, or `new`, with rationale.
2. Prefer one integration entrypoint and adapters over copying whole folders. Avoid redundant state stores, duplicate schemas, duplicate model clients and parallel preprocessing pipelines.
3. Keep the existing fixed adversarial baseline runnable and use its original data IDs, prompts/configuration (except clearly documented adaptations) for matched-budget comparisons.
4. Add regression tests confirming reused data loader and API schemas behave consistently with their upstream versions; tests for modified PPO/GAE must cover a role acting after multiple other-role steps.
5. Pin both upstream commits and record any local changes; retain license notices for copied/adapted code. **No silent behavioral change** in reused components.
6. Before writing new code, audit for existing equivalent functionality in *both* repositories and state exactly why new code is required.

**Success criterion for reuse:** The only substantial new logic should be courtroom-specific state/turn routing, argument ledger and lifecycle, action legality/target selection, reward, and adapters bridging the existing LLM framework to the existing PPO machinery. Reuse is a priority, but never at the cost of incorrect turn-based credit assignment, label leakage or invalid episode termination.

## 3. Dataset and leakage contract

**Data source:** https://github.com/Crowd-AI-Lab/cocolofa

```
data/cocolofa/{train,dev,test}.json
```

Call `select_task(load_split(path), 'classification')` to select labeled fallacious comments only. Preserve official splits and sample IDs. Ground-truth label is available **only** to reward/evaluation code, never to role prompts, policy observations or cached dialogue. Preserve `title`, `parent_comment`, `comment`; default model context `sample.model_input(context='paper')`, i.e. title + immediate parent + target. Do not import article content or distant parents unless explicitly running a controlled ablation. Use the same context for all baselines.

The `Sample` structure contains `sample_id`, `article_id`, `comment_id`, `split`, `title`, `comment`, `parent_comment`, `article`, `fallacy`, `missing_parent`. The loader resolves a parent **within the same article**; missing parent remains empty. `ModelInput` is allowlisted to `title`, `parent_comment`, `comment`, optionally `article` in a separate context mode.

Before training, make **grouping checks by article/thread** for dev and test and record duplicate/near-duplicate overlaps; do not reshuffle official splits silently. Audit feature leakage from precomputed outputs and caches.

## 4. Formal environment: turn-based partially observable stochastic game

Use a stochastic game rather than claiming one flat single-agent MDP:

\[
\mathcal{G}=(N,S,\{A_i\},T,\{O_i\},\{R_i\},\gamma),\quad N=\{P,D,J\}.
\]

Exactly one `active_role` takes an RL action at each **global decision time** `t`. Action triggers an LLM call (unless it is a code-only action), validation and a deterministic update to the shared ledger; stochastic LLM output makes transitions stochastic. All roles are fixed for the entire episode.

### 4.1 Global environment state

```
CourtState:
  case_input: ModelInput             # public, immutable
  active_role: Prosecutor|Defender|Judge
  phase: INITIAL_CHARGE|DEFENSE_REVIEW|JUDGE_REVIEW|FOLLOWUP|TERMINAL
  charge_label: one_of_eight | null
  candidate_labels: <=2 alternatives (V1 constraint)
  claims: list[Claim]                # capped total created, not just active
  argument_events: list[Event]      # canonical, append-only
  pending_request: Request | null
  role_status: {prosecutor_rested, defender_rested}
  action_history: list[(role, action, target, fingerprint)]
  remaining_decisions: int
  remaining_llm_calls: int
  remaining_tokens: int
  budget_usage: {calls, input_tokens, output_tokens}
  belief: float[8] | null           # from a fixed independent assessor, optional
  done: bool
  forced_verdict: bool
  final_label: one_of_eight | null
```

Gold labels are stored **outside** the policy-visible `CourtState`, e.g. in an environment-private `RewardContext`, never serialized into prompt/observation or replay artifacts consumed by an agent.

```
Claim:
  claim_id: stable id
  author: role
  label: label under discussion
  proposition: concise asserted reasoning defect or defense
  source_span: exact quote + offsets where available
  supporting_ids: list[claim_id]
  attacks_ids: list[claim_id]
  status: OPEN|DISPUTED|RESPONDED|CONCEDED|UNRESOLVED|CLOSED
  challenge_count: int
  response_count: int
  normalized_fingerprint: string
```

**No objective logical correctness is inferred from the status.** A conceded claim is an accepted position by a participant, not a fact or a proof that the label is right.

### 4.2 Visible observations

An observation is `(global_features, claim_features_and_masks, legal_action_mask)`. Include source text/claim contents for the action-executing LLM, but make RL features compact and deterministic where possible:

- **Global**: turn index, remaining resource budgets (normalized), active charge (one-hot), whether defendant contested, number of unresolved claims, number of distinct tested label hypotheses, pending request type, prior action counts, optional fixed-assessor 8-way probabilities and entropy.
- **Per-claim**: frozen text embedding (small model or API, cached), label one-hot, author, status, exact-grounding flag, number of challenge/response turns, dispute flag, age and hashed semantic dedup indicator.
- **Role-specific masking**: Prosecutor may only defend an open challenged claim and revise to an alternative not already exhausted; Defender can only challenge a claim not previously challenged and concede a known claim; Judge can only request admissible additional replies, or deliver a verdict when legal.

The RL observation must contain sufficient claim-level information to identify **which** claim deserves attention; a global 20-D vector alone cannot distinguish two equally sized disputes. If using a compact aggregate representation initially, measure the loss from omitting claim embeddings and use a pointer head when moving to target-specific actions.

**Visibility**: every role can see the public case and admissible public ledger. No agent observes `gold_label` or judge's private reward information. Judge's **public** current belief can be shared or hidden as a controlled ablation: exposing it may encourage confidence manipulation. Prefer hide belief from P/D in V1 and let Judge see its own fixed-assessor distribution.

### 4.3 Markov sufficiency

The full state must preserve the `pending_request`, exhausted targets, action history fingerprints, accepted/contested status and budgets so next-step legal actions can be derived without consulting hidden past text. Compact RL observations are partially observable approximations; do not label the observation itself a full MDP state.

## 5. Actions, target selection and validity

A role-conditioned hierarchical policy selects `(action_type, target)` with a legal mask:

\[
\pi_i(a,z\mid o) = \pi_i(a\mid o)\pi_i(z\mid a,o).
\]

**V1:**

| Role | Action | Target | Effect |
|---|---|---|---|
| Prosecutor | `ACCUSE` | 8-way label | First grounded accusation; only in `INITIAL_CHARGE` |
| Prosecutor | `DEFEND_CLAIM` | disputed claim ID | One substantive targeted answer |
| Prosecutor | `REVISE_CHARGE` | unused label | Replace charge with grounded explanation; max 1 revision |
| Prosecutor | `REST_CASE` | none | Give up further prosecution turns, not a verdict |
| Defender | `CHALLENGE` | eligible claim ID | Specific challenge to evidence or inference; max 1 challenge per claim |
| Defender | `PROPOSE_ALTERNATIVE` | unused label | One grounded alternative (max 1 proposal in V1) |
| Defender | `CONCEDE` | eligible claim ID | Agree with that claim, not necessarily the class |
| Defender | `REST_DEFENSE` | none | Give up further defense turns, not necessarily agree |
| Judge | `REQUEST_PROSECUTOR` | eligible claim ID | Route a targeted question to Prosecutor |
| Judge | `REQUEST_DEFENDER` | eligible claim ID | Route a targeted question to Defender |
| Judge | `VERDICT` | 8-way label | Terminal verdict; no separate LLM needed to select label if policy head predicts it |

**Selection and execution semantics:** First sample the action type, then sample a valid target from that action's target list. The sum of type and target log probabilities is stored for PPO. Always apply identical masks during rollouts and PPO recomputation. If no target for an action, mask its action type. At least one legal action must exist (forced verdict fallback).

**LLM roles execute text generation only.** `REST_CASE`, `REST_DEFENSE`, `CONCEDE` (if just structured acknowledgement), and `VERDICT(label)` can be code-only changes or minimal templated explanations; avoid unnecessary model calls. A final short judge explanation may be generated **after** verdict as a non-RL evaluation artifact; record its tokens separately, and do not allow it to change the predicted label.

## 6. Episode and debate-round semantics

**Episode:** one CoCoLoFa positive example, from reset to final verdict.  
**Global RL step:** one legal decision by exactly one active role.  
**Debate round:** optional logical group of claim → challenge → response/review, **not** a fixed loop of all three actors.

### 6.1 Turn routing (environment-controlled)

```
reset -> Prosecutor.ACCUSE
      -> Defender.CHALLENGE / PROPOSE_ALTERNATIVE / CONCEDE / REST_DEFENSE
      -> Judge.VERDICT / REQUEST_PROSECUTOR / REQUEST_DEFENDER
      -> requested role responds (only targeted legal actions)
      -> Judge review
      -> ... until verdict or forced verdict
```

More exact: action masks are **phase-sensitive**. `REQUEST_PROSECUTOR(C1)` sets `pending_request=PROSECUTOR(C1)` and activates P. When P responds, mark the request resolved and reactivate Judge. Analogous for D. An existing unresolved request blocks unrelated moves until it is answered, explicitly refused (`REST_*`), or exhausted by budget. Judge cannot indefinitely ask the same question again. An alternative charge creates a new admissible question about **comparison** before verdict; avoid a new unconditional full defense cycle.

**Necessary first defense exposure:** Prosecutor cannot unilaterally end a case before at least one Defender opportunity; Judge cannot choose final verdict until accusation has been exposed to Defender (or an explicit forced budget exception). This ensures the policy is not simply a prosecutor-only classifier.

### 6.2 Termination and truncation

- **Terminated:** Judge selected `VERDICT(label)`; outcome is scored once.
- **Budget exhausted:** force a Judge verdict via its masked label head (or a specified frozen arbiter fallback), log `forced_verdict=True`; then end. Do not drop hard samples.
- **System failure:** retry malformed responses with a finite budget, then mark an infrastructure failure distinct from a wrong prediction. Training may exclude corrupted tool/API failures with audit; evaluation reports failure coverage instead of assigning or filtering silently.
- **Do not reward `REST_DEFENSE` for its own sake.** Stopping is learned via future terminal payoff vs added cost.

**Suggested starting caps** (tune on dev only): at most 8 RL decisions beyond setup, 3 total claims and 1 challenge + 1 response per claim, 1 prosecutor revision, 1 defense alternative; token/call budget and forced-verdict rate recorded. Run sensitivity tests at 4/6/8/12 decisions because strict caps can hurt hard samples.

## 7. Anti-repetition and wrong-decision control

### 7.1 Layer 1 — deterministic legal-action masks (before LLM calls)

- Never reopen `CONCEDED` or `CLOSED` claims without new admissible evidence (V1: fully disallow reopening).
- Do not offer `(role, action_type, claim_id)` twice if already consumed, except where an explicit different lifecycle phase requires a response.
- A claim can receive at most one challenge and one reply in V1.
- Judge may not request the same unanswered question again; repeated request keys are exhausted.
- Cannot propose the same alternative label twice; prohibit cycling `label A → B → A` in V1.
- `VERDICT` is always legal once the initial defense opportunity occurred; when all follow-up options are exhausted it is the only legal Judge action.

### 7.2 Layer 2 — canonical record + semantic dedup

Compute fingerprint from `(normalized claim, label, source span, role, intended relation)` and embed normalized text. Before inserting a new claim, detect exact duplicate and high-similarity candidates **under the same relation and evidence conditions**. Similarity is a *flag for review*, not conclusive proof of duplicate: two propositions can look similar yet differ in negation, scope, conclusion or label. Require explicit evidence of an actually new premise, inference, distinction or source span for a revised accusation. A duplicate is rejected and consumes a small non-recoverable cost; structured reasons are logged.

### 7.3 Layer 3 — grounded arguments

Require structured LLM outputs: `claim_id`, `label`, `supported_quote`, `mechanism`, `attacks_claim_ids`, `answer_to_pending_request` where relevant. Validate exact quote/span against the target comment (and separately track parent/title context); reject invented quotations, inconsistent labels, missing targets, invalid JSON. An LLM's assertion that an argument is correct is **not** proof of correctness.

### 7.4 Layer 4 — independent Judge / no belief laundering

Do not use a self-reported Judge confidence change as a direct performance metric. If including a fixed assessor's belief in observation or shaping, freeze its model and prompt, hide gold, calibrate on training/development only, and test susceptibility to persuasion-only text. Verify final labels against gold and analyze early wrong verdicts, not just shorter episodes.

## 8. Reward and credit assignment

### 8.1 Minimal V1 reward (primary baseline)

**Shared terminal payoff** for all roles:

\[
R_T = +1\ \text{if}\ \hat y=y^*,\quad -1\ \text{otherwise}.
\]

**Per action cost:**

\[
r_t^{cost} = -c_{step}-c_{token}\cdot\text{new_tokens}_t-c_{call}\cdot\text{new_calls}_t-c_{invalid}\cdot\mathbf{1}[invalid].
\]

Do not use reward `+accuracy` or `+judge_confidence` on *every* intermediate step: repeated state-level reward can encourage delay and confidence gaming. Default V1: no additional direct bonus for `CHALLENGE`, `CONCEDE`, `REVISE` or `STOP`. Example *candidate*, not tuned settings: `c_step=0.01`, `c_token=1e-5`, `c_call=0` when token cost already captures calls, `c_invalid=0.1` (invalid should usually be prevented by masking).

Return is computed over the **global event timeline**, with terminal reward assigned to the terminating transition and backpropagated via GAE. Rewards for other decisions can include cost only. Reward computation may read gold; no actor, critic input, observation encoder or text executor may read gold.

### 8.2 Optional shaping, **separate ablation**

Potential-based shaping (not raw belief delta):

\[
F(s_t,s_{t+1})=\gamma\Phi(s_{t+1})-\Phi(s_t),
\quad \Phi(s)=\alpha\log\max(p_{assessor}(y^*\mid s),\epsilon).
\]

For a finite episodic objective, make terminal potential zero and handle truncation consistently. Evaluate whether this actually improves accuracy or simply exploits the assessor. The assessor is a *training-only reward oracle*, not the same LLM as the role producing the action. Start without shaping, then compare with and without on identical data/seeds. Reward normalization should be fit and tracked carefully; distinguish policy scores from raw environmental outcomes.

### 8.2A Dense, progress-based reward (recommended V2 experiment)

Keep the shared final classification objective. Unlike the original CREW training reward, **never award the same state-level score again at every timestep**. Score the *change in classification evidence* following each action.

For each public ledger state, compute `q_t = q(y | case, validated_ledger_t)` using a frozen, external, eight-class assessor. The assessor must not see the gold label. Reward computation (training only) may access `y*` from the CoCoLoFa train split. Freeze the assessor, encoder and calibration during policy training. It should not be the current Judge's self-reported confidence.

Define `Phi(s) = alpha * clamp(log(max(q_s[y*], 1e-4)), -6, 0)` for nonterminal states and **`Phi(terminal)=0`**. On every active-agent transition:

`r_t = 1[terminated] * (2*1[verdict==y*]-1) + gamma*Phi(s_next)-Phi(s_now) - 0.01 - 1e-5*tokens_t - 0.1*invalid_t`

Start with `alpha=0.25`, `gamma=0.99` as trial values, not calibrated optima. The potential-based term supplies a dense progress signal without paying repeatedly for a high-confidence state; with a zero terminal potential it telescopes over the discounted episode. Do not separately add raw probability deltas, entropy reduction or another repeated per-step confidence reward.

**Credit assignment:** evaluate the assessor after a meaningful ledger change and assign the potential difference only to that acting transition. A Judge request may only change turn routing, not substantive evidence; it usually receives just action cost now and gets downstream credit through GAE. `CONCEDE` and `REST_DEFENSE` never receive an automatic bonus. A revision that reduces belief in the gold class produces negative progress, even if the agent seems persuasive.

**Illustrative assessor values:** gold-label probability 0.30 -> 0.25 (misleading accusation: `0.25*ln(0.25/0.30)=-0.046`), then 0.25 -> 0.60 (valid defense: `+0.219`), then 0.60 -> 0.85 (corrected accusation: `+0.087`). These are local progress quantities for illustration, not the complete discounted reward including terminal reset and costs.

**Anti-gaming policy:** use exact quote grounding, claim lifecycle, action masks, duplicate detection, and one-time evidence-ID tracking as **hard environment constraints**, not endlessly repeatable positive rewards. A small capped one-time novelty/validity bonus is an *optional ablation only* (whole-episode cap <= 0.1), and must be granted only for independently checked, genuinely new evidence; never reward verbosity, disagreement, claim count, concede count or Judge agreement directly. Log reward components separately.

**Evaluator risks and tests:** the frozen assessor may be manipulated by agent rhetoric. Train/calibrate it using train data only; audit reward progress on a sample of trajectories with a different evaluator; compare terminal-only V1 vs dense V2 on dev macro-F1, accuracy, token costs, calibration, repeat rate, and multiple seeds. No policy, critic, LLM prompt, agent-facing cache key or observation may receive `y*` or computed gold-specific shaping values. The assessor's predictions are training signals, not ground truth.

### 8.2B CREW-inspired component-delta reward (recommended next experiment)

**Design intention.** CREW rewards the *change in quality* of the component an action improves (local knowledge, global knowledge, feedback, draft) and also credits improvements to the final draft. For this courtroom, translate that principle into **three separately scored components**, while leaving the final 8-class accuracy as the shared target. This is an experimental reward, *not* a claim of proven policy invariance. Retain 8.1 and 8.2A as ablations.

- `Q_local_i`: quality of the **specific action result** (grounded prosecutor argument, valid defense counterexample/alternative, or judge's targeted request); use only **verified deltas in the role's own bounded ledger**, never self-rated eloquence. A prosecutor is not rewarded for a *confident but wrong* charge; a defender is not rewarded merely for disagreeing.
- `Q_board`: quality of the **shared resolved-argument board**: fraction of *unique, source-grounded, noncontradictory* claim/evidence units with correct recorded dispute status; score is normalized, duplicate IDs add nothing, and rejecting a bad claim can improve quality. Avoid any reward just for increasing count.
- `Q_decision`: the **fixed external assessor's** quality of the case-supported classification on eight labels, e.g. bounded log probability of `y*` using the current, validated public ledger. Its weights and calibration are frozen; no gold enters the assessor's input, although train gold is used privately to compute this reward. **Do not use the acting Judge's self-reported confidence.**

For each *actual active-role* global step `t`, let `u_t = t / max(1, H-1)` and `w_t = clip(0.2 + 0.6*u_t, 0.2, 0.8)`. An illustrative CREW-style reward:

```
delta_local = Q_local_i(s_next) - Q_local_i(s_now)
delta_board = Q_board(s_next) - Q_board(s_now)
delta_decision = Q_decision(s_next) - Q_decision(s_now)

progress = (1-w_t) * (0.4*delta_local + 0.6*delta_board) + w_t*delta_decision
r_t = 0.3 * clip(progress, -1, 1) - 0.01 - 1e-5*generated_tokens_t
      - 0.1*invalid_action_t
      + (1 if correct_final_verdict else -1 if wrong_final_verdict else 0)
```

All weights, normalization, and `H` are **starting hyperparameters**, to be selected by train/dev and not presented as established optimal values. **Normalize** the per-component deltas using fixed train-derived statistics (or a bounded scale) *before* weighted mixing; otherwise one metric can overwhelm the others. `Q_local_i` must be persistent over the episode (e.g. cumulative, deduplicated *validated* contribution), rather than an unrelated absolute score of the latest text: otherwise consecutive differences are nonsensical.

**Credit allocation:** only the active agent takes a PPO action. A Judge request usually does not add evidence and so receives little/no immediate component-delta reward, but its eventual effect is credited through the global timeline and GAE. A Judge verdict receives the terminal score, and its action can also incur costs. `CONCEDE`, `REST_DEFENSE`, and repeated objections do not earn a fixed bonus. A successful critique of a wrong charge can increase both `Q_board` and `Q_decision`.

**Do not reuse CREW's training expression `similarity_t + 0.1 * environment_reward_t`.** Repeatedly giving an unchanged level score is particularly dangerous for a variable-length courtroom; it can reward waiting, verbosity, and repeated claims.

**Essential tests and caveats:** (a) repeated no-op must have `delta_local=delta_board=delta_decision=0`; (b) a wrong but persuasive charge must not receive a large positive score; (c) a grounded defense that rejects a wrong charge must be able to improve score; (d) stopping or conceding does not earn a bonus on its own; (e) component improvements must not overwhelm terminal correctness or the learned actor may optimize the surrogate instead. Component-delta shaping generally **does not guarantee preservation of the terminal-optimal policy**. To test that, compare against 8.2A, the potential-based variant, and terminal-only 8.1; report macro-F1, accuracy, calls, tokens, rounds, duplicate rate and label-specific confusion on held-out dev/test.

**Efficient implementation:** reuse CREW's `get_q_torch`, `step()`-side old-vs-new component scoring, action-type reward dispatch, logging and normalization *patterns*; implement new courtroom metrics and turn-based transitions in adapters. Reuse `test_debate_agents`' data loader, role prompts, evidence grounding, structured schemas and LLM response cache. Avoid extra paid LLM grading per step when cheap deterministic checks and a frozen small classifier suffice.


### 8.3 Credit assignment in turn-based play

Shared outcome reward naturally propagates to all roles through their earlier decisions; it does **not** mean every agent takes an action at every step. Store the actual acting role, masks and action logprobs. For role-specific actor updates, include only steps on which that role acted. If using per-role trajectories rather than a unified timeline, account for elapsed time between decisions (`gamma^Delta_t`) and intermediate costs to avoid incorrect discounting. Simpler V1: unified global-time trajectory with a role-specific policy head and centralized value estimate, updating the active actor only. Compare role-specific IPPO and centralized-critic MAPPO; do not assume one wins.

## 9. Training pipeline

### 9.1 Recommended progression

1. **Behavioral/heuristic baseline:** Run the existing one-pass Prosecutor → Defender → Arbiter on train/dev with exact same input context and model; capture ledger-format traces. Set fixed-3-call reference cost and accuracy.
2. **Offline smoke / warm-start (optional):** Create a simple conservative heuristic that favors challenge of one unsupported claim, otherwise concede/rest and verdict. Pretrain action-head imitation if online PPO is unstable. Do not give PPO credit for forced heuristic actions using its own sampled-action log-probability; mark heuristic steps off-policy and exclude them from the PPO objective or use a proper behavior-policy correction.
3. **Online PPO:** Freeze LLM weights/prompts/embedding encoder/assessor. For each train sample run a bounded episode, collect actions, reward, logprob, critic value, masks, tokens, next state, done flags; update after multiple episodes (rollout batch), not necessarily after every expensive episode.
4. **Validation and model selection:** Dev macro-F1/accuracy primary; enforce token/call budget constraints or use a Pareto frontier. Test is run after hyperparameters and prompts are frozen; never tune by test failures.

### 9.2 Pseudocode

```python
for epoch in range(num_epochs):
    for batch in train_batches:
        trajectories = []
        for sample in batch:
            obs = env.reset(sample)  # gold in RewardContext only
            episode = []
            while not env.done:
                role = env.active_role
                action_mask, target_masks = env.valid_actions(role)
                a, target, logp = actor[role].sample(obs[role], action_mask, target_masks)
                old_value = critic.value(env.critic_observation())
                next_obs, reward, terminated, truncated, info = env.step(role, a, target)
                episode.append((role, obs[role], action_mask, target_masks,
                                a, target, logp, old_value,
                                reward, terminated, truncated, info))
                obs = next_obs
            trajectories.append(episode)
        advantages, returns = compute_global_time_gae(trajectories, gamma, gae_lambda)
        # Recompute logp with IDENTICAL old masks; update only active role actor.
        update_ppo_role_actors_and_critic(trajectories, advantages, returns)
    evaluate_on_dev_with_frozen_policy()
```

**Critical distinction:** when computing GAE at episode end, `terminated` masks out future values; for a true time-limit truncation that does not force a verdict, bootstrap correctly instead of equating truncation with task completion. Recommended contract resolves the limit by forced verdict and scores it terminally.

### 9.3 Rollout storage contract

```
Transition:
  sample_id, global_step, role, phase
  observation_features, claim_features
  action_type, target_id, action_mask, target_mask
  action_logprob, critic_value
  llm_output_hash, output_contract_status
  rewards: {terminal, step_cost, token_cost, invalid, shaping}
  next_state_id, terminated, truncated, forced_verdict
  token_usage, model_id, prompt_version, config_hash
```

Checkpoint all actors, critics, optimizers, normalization statistics, training split selection, random seeds, hashes of prompt/schema/LLM snapshots, and dataset provenance. Save best by dev validation, not training reward alone.

### 9.4 Resource requirements and caching

Small MLP action/target heads and PPO can run on CPU. LLM through NVIDIA or another provider runs remotely; most expense is LLM calls and latency, not backprop. A local encoder may use CPU with cached embeddings; GPU is optional for encoder speed or self-hosted LLMs. Cache by source sample+context, role, phase, selected action/target, **canonical state and relevant history**, prompt/schema, model snapshot, decoding parameters and seed when supported. **Never** reuse an action result solely because role/action matches on the same sample—its meaning changes with debate history. Stochastic online RL rollouts need diverse outcomes; treat cache hit rates and sampling policy as experimental variables.

## 10. Concrete example (illustrative; not an actual run)

Input: "We've always done it this way, so it must be the best way." Gold label (training reward only): **Appeal to Tradition**.

| Global step | Role | Policy choice | Ledger transition | Further LLM call? |
|---|---|---|---|---|
| 0 | Prosecutor | `ACCUSE(Appeal to Tradition)` | C1 created with quote and inferential mechanism | Yes |
| 1 | Defender | `CHALLENGE(C1)` | C1 `DISPUTED`: asks if longevity is truly being used as justification | Yes |
| 2 | Judge | `REQUEST_PROSECUTOR(C1)` | Pending question directed to P | No (routing only) |
| 3 | Prosecutor | `DEFEND_CLAIM(C1)` | C1 `RESPONDED`, points to "so" causal bridge | Yes |
| 4 | Judge | `VERDICT(Appeal to Tradition)` | Episode terminates and scores reward | No (optional post-hoc explanation) |

A different correct policy might skip follow-up when the defender concedes, reducing calls. A wrong initial charge can be revised once when meaningful new evidence warrants it. Judge is not obliged to accept either party's label solely because they agree.

## 11. Evaluation design and ablations

Use identical CoCoLoFa classification positives, same frozen LLM model, context and token/step budgets where possible.

| Baseline / ablation | Purpose |
|---|---|
| Single LLM 8-way classification | No debate baseline |
| Fixed Prosecutor → Defender → Arbiter | Original branch baseline |
| Random legal action policy | Demonstrates environment constraints alone are not enough |
| Heuristic early-stop policy | Tests whether PPO beats a hand-written controller |
| Learned policy full model | Proposed method |
| No anti-repeat constraints | Identify redundancy savings and effects on accuracy |
| No claim-level features | Test need for claim-target information |
| No token/step cost | Quantify excess deliberation |
| No belief shaping / with shaping | Test risk/benefit of evaluator-driven rewards |
| Different max decision budgets (4/6/8/12) | Sensitivity / accuracy-cost Pareto |
| IPPO vs centralized critic | Evaluate credit-assignment choice |

Report: classification accuracy, macro-F1 across all 8 labels, per-label F1, confusion matrix, exact sample coverage, mean/median/p90 token use, mean LLM calls, global decisions, forced-verdict rate, invalid output rate, repeated-semantic-claim rate, early correct/wrong verdict rate, concede precision (audit), accuracy by budget and multiple random seeds with uncertainty intervals. Note: terminal reward already exploits labels for training; do not use dev/test gold in online policy selection.

## 12. Implementation structure

```
src/courtroom_rl/
  env.py                # reset / legal_actions / step / termination / reward
  schemas.py            # Case, Claim, Event, Request, State, Transition
  ledger.py             # append-only claims, status transitions, source grounding
  masks.py              # state-dependent action + target legality
  dedup.py              # canonicalization, semantic duplicate safety checks
  observation.py        # global features, claim embeddings, role observations
  llm_executor.py       # adapt existing prosecutor/defender prompts by action
  policies.py           # 3 role-specific actors + claim-pointer heads
  critic.py             # per-role IPPO or centralized MAPPO critic
  reward.py             # terminal label, step/token costs, optional shaping
  buffer.py             # global-timeline transitions and GAE
  train.py              # frozen LLM + online PPO, batching, checkpoint
  evaluate.py           # baselines, metrics, matched budget evaluation
  replay.py             # deterministic trace replay and debugging
configs/courtroom_rl.yaml
scripts/smoke_courtroom.py
tests/test_courtroom_*.py
```

Do not modify original dataset files or overwrite baseline output directories. Keep full run configs and source version recorded for reproducibility.

## 13. Acceptance tests before expensive API training

1. Dataset selection uses train classification positives only; `gold_label` cannot appear in policy observations or any prompt.
2. At reset, only Prosecutor initial accusation is legal; no invalid target ever sampled.
3. Defender has at least one initial opportunity before ordinary Judge verdict.
4. After a claim is challenged once, same claim cannot be challenged again by renaming/rephrasing without substantive new content.
5. `REST_DEFENSE` does not imply concession or auto-verdict; `CONCEDE(C1)` does not concede all claims.
6. Judge request routes to the correct active role and cannot repeat an exhausted request.
7. Budget exhaustion forces a logged final verdict and scores the case; hard cases are not silently dropped.
8. Invalid source quotes and JSON are rejected with bounded retries and explicit failure logs.
9. Terminal reward occurs exactly once and is visible only in training/evaluation.
10. All action/target masks used for PPO logprob recomputation match rollout masks.
11. Unified time-indexed GAE handles gaps between turns by a role and correct terminal masks.
12. Freeze model/prompts/evaluator during train and evaluation; no test leakage.
13. Compare fixed baseline against the same input selection and report all cases (including failures).
14. Replay one cached trace produces the same normalized ledger and verdict.
15. Trace includes exact decision reason, target, changed ledger fields, tokens, stop reason and reward components for every step.

## 14. Recommended first milestone and open design risks

**First milestone:** working CPU-only `CourtroomEnv` using the existing branch's CoCoLoFa loader and LLM API contracts, legal masks, bounded claims, turn routing, a simple frozen random/heuristic policy, deterministic replay and fixed-baseline comparison. Then add PPO, then explore learned target selection and reward shaping. This yields interpretable failure traces before paying for thousands of online episodes.

**Main unresolved research risks:** sparse terminal reward and high-variance gradient; semantic dedup false positives; over-restrictive action masks suppressing valid correction; overconfidence-driven early incorrect verdicts; training using an evaluator with hallucinations; high LLM latency; biased data distribution of the separate adversarial-error subset; policy exploiting deterministic cached outputs; comparing unequal budgets; insufficient statistical significance. Each requires a dedicated diagnostic/ablation rather than assumed resolution.

## 15. References

- CREW GitHub: https://github.com/YenPBao/CREW-Collaborative-MARL
- CREW environment: https://github.com/YenPBao/CREW-Collaborative-MARL/blob/main/src/rl_env/rwg_env.py
- CREW training: https://github.com/YenPBao/CREW-Collaborative-MARL/blob/main/src/train_self_supervised.py
- CREW GAE buffer: https://github.com/YenPBao/CREW-Collaborative-MARL/blob/main/src/training/ippo_trainer.py
- Courtroom baseline branch: https://github.com/HuyL13/test_debate_agents/tree/feat/adversarial-dialectical-debate
- Courtroom execution: https://github.com/HuyL13/test_debate_agents/blob/feat/adversarial-dialectical-debate/src/adversarial_debate.py
- Courtroom prompts: https://github.com/HuyL13/test_debate_agents/blob/feat/adversarial-dialectical-debate/src/adversarial_prompts.py
- Data loader: https://github.com/HuyL13/test_debate_agents/blob/feat/adversarial-dialectical-debate/src/data/loader.py
- Dataset: https://github.com/Crowd-AI-Lab/cocolofa
