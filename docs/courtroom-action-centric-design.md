# Courtroom-MARL — Action-Centric Technical Design (V3)

**Status:** implementation specification; proposed, not experimentally validated  
**Date:** 2026-10-13  
**Task:** CoCoLoFa **8-way fallacy classification**, gold-positive only.  
**Core principle:** **RL decides WHAT STRATEGIC ACTION to take; LLM decides WHICH hypothesis/claim to address, WHICH label to argue for, and HOW to reason.**  
**Do not implement RL label selection, RL claim-ID targeting, or a separate pre-analysis LLM action proposer in V1.**

## 1. Goals and invariants

1. Keep fixed roles: `Prosecutor`, `Defender`, `DialecticalArbiter` (Judge).
2. At episode initialization, **Prosecutor LLM generates exactly three distinct candidate fallacy labels** from the official 8 classes, plus one or two text-grounded supporting claims per hypothesis. This is **not** an RL action in V1.
3. Preserve a **Hypothesis Pool** and **Claim Ledger**; hypotheses represent possible labels, while claims represent independently examinable reasons or objections.
4. Train three **role-specific RL actors** that select **high-level action types only**; content decisions stay with frozen LLM executors.
5. The Judge LLM outputs one of **all eight labels**, not necessarily a member of the initial Top-3; Top-3 errors must remain recoverable.
6. Prevent pointless repetition with validation, masks, deduplication, budgets, and stopping rather than encouraging verbose debate.
7. Optimize held-out macro-F1/accuracy **under matched inference budgets**, not rhetorical persuasiveness or victory by either side.
8. Gold labels are accessible **only** to the private training reward/evaluation pipeline; never feed gold or gold-derived rewards into actor observations, prompt texts or model-visible caches.

## 2. Mandatory maximal code reuse

**Always inspect both repositories before writing a component. Prefer import → adapter → subclass/extension → new implementation, in that order. Document in the PR why each new module could not be reused.** Do not copy modules into a fork unnecessarily.

### 2.1 `HuyL13/test_debate_agents`, branch `feat/adversarial-dialectical-debate`

https://github.com/HuyL13/test_debate_agents/tree/feat/adversarial-dialectical-debate

Reuse with minimal changes:

- `src/data/loader.py`: `Sample`, `ModelInput`, `load_split`, `select_task`, paper context (`title + parent_comment + comment`).
- `scripts/prepare_data.py`: pinned upstream CoCoLoFa train/dev/test and `provenance.json`. Keep split/provenance integrity, gold-positive filtering, and source hashes.
- `src/adversarial_prompts.py`: existing formal Prosecutor, Defender and Arbiter role definitions. Extend **action-specific user instructions**, not the core role behavior.
- Existing schemas, quote grounding and validators: extend with Top-3, hypothesis IDs, claim IDs, statuses, alternative proposals; preserve validation of exact quotes in `comment`.
- Existing LLM API client, retry/error handling, cache, tracing, sample manifests and evaluator. Extend cache keys to include `action_type`, ledger revision, role, prompt/schema/model fingerprints, decoding setup.
- `src/adversarial_debate.py`: preserve the **one-pass non-RL baseline** for fair comparisons. Introduce a separate adapter for RL episode orchestration rather than replacing the reference path.

**Caution:** the branch's adversarial classification example config points to `data/dev_classification_errors`, a diagnostics subset. RL training must use the normal `data/cocolofa` **train**, and evaluation must not train on dev/test.

### 2.2 `YenPBao/CREW-Collaborative-MARL`

https://github.com/YenPBao/CREW-Collaborative-MARL

Reuse or adapt:

- `src/rl_env/rwg_env.py`: `reset/get_obs/step` **interfaces**, component quality **delta** computation, token and action statistics, and action-structured observation **design pattern**.
- `src/networks/actor.py`, critic architecture: lightweight MLP skeleton; instantiate **three role-specific actors** with distinct action dimensions.
- `src/training/ippo_trainer.py`: buffer/GAE concepts; adapt for **turn-based global-time transitions** (details below).
- `src/train_self_supervised.py`: PPO clipped loss, optimization, checkpointing, epoch/rollout instrumentation and cold-start idea; do not copy hardcoded 20-dimensional flattening or shared 4-action policy.
- `src/agent/action.py`: dispatch abstraction, but use Courtroom-specific action handlers.

**Do NOT copy unchanged:** CREW's parallel multi-agent `step()`, fixed-step-only termination, 4 fixed actions, its particular text-similarity-to-reference-draft reward, or training reward `sim_t + 0.1 * r_env_t` repeated at every step. These do not match a sequential adjudication task.

## 3. Roles and responsibility contract

| Role | RL actor selects | Frozen LLM executor selects / generates |
| --- | --- | --- |
| Prosecutor | `SUPPORT`, `REVISE`, `REST` | The hypothesis and claim to support; evidence and rebuttal; whether/how to revise candidate labels |
| Defender | `CHALLENGE`, `PROPOSE_ALTERNATIVE`, `CONCEDE`, `REST` | Which hypothesis/claim to challenge; whether an alternative is actually justified; alternative label; rebuttal text |
| Judge | `REQUEST_SUPPORT`, `REQUEST_REBUTTAL`, `VERDICT` | Which unresolved issue to ask about when requesting; final label among 8 and grounded verdict rationale |

**Never silently promote an LLM-suggested action into the policy's action choice.** Actor chooses `CHALLENGE`; the LLM must comply and decide which claim to challenge. If no valid target exists, the action should have been masked. Unexpected no-op/invalid content is logged and penalized, not treated as useful evidence.

The Judge actor's `VERDICT` controls **when** to stop, not **which fallacy** is predicted. Only the Judge LLM chooses the verdict label. This preserves a strategic, not semantic-classification, RL learning objective.

## 4. Environment state

Each episode processes exactly one gold-positive CoCoLoFa comment.

```python
@dataclass
class Hypothesis:
    id: str                      # H1, H2, H3, ...
    label: str                   # one of official 8 fallacy labels
    initial_rank: int | None
    claim_ids: list[str]
    status: str                  # ACTIVE | CHALLENGED | WEAKENED | SUPPORTED | REJECTED
    visits: int = 0

@dataclass
class Claim:
    id: str                      # stable C1, C2, ...
    hypothesis_id: str
    author_role: str
    proposition: str
    quote: str                   # exact source span or explicitly flagged missing
    kind: str                    # SUPPORTING | CONTRADICTING | REBUTTAL
    status: str                  # OPEN | DISPUTED | RESPONDED | RESOLVED | UNRESOLVED
    challenge_count: int = 0
    response_count: int = 0

@dataclass
class CourtroomState:
    case: ModelInput
    hypotheses: list[Hypothesis]
    claims: list[Claim]
    evidence_units: list[dict]
    events: list[dict]           # append-only auditable global turn history
    active_role: str             # Prosecutor | Defender | Judge
    pending_request: dict | None
    rl_steps: int
    max_steps: int
    tokens_used: int
    terminal: bool
```

`gold_label` is kept in an **environment-private evaluator wrapper**, not in `CourtroomState` passed to LLMs/actors. `Hypothesis.status` should reflect **validated dialogue state**, not ground-truth logical correctness. A disputed claim does not imply the hypothesis is false. `CONCEDE` is a statement by a role, not an oracle ruling.

## 5. Episode control and transitions

```text
reset(sample)
  -> load ModelInput, reset all per-episode state, tokens, caches/usage counters
  -> Prosecutor LLM: TOP3_INIT (exactly 3 distinct labels, 1–2 claims/label)
  -> validate labels, quoted evidence, schema; store H1..H3 and C1..Ck
  -> active_role = Defender

loop (until verdict or budget cap):
  obs = get_obs(active_role)  # code-derived, action-centric features + mask
  action_type = actor[active_role].sample(obs, mask)
  if action_type == VERDICT:
      Judge LLM picks one of 8 labels and explains -> TERMINATE
  elif action_type in [REQUEST_SUPPORT, REQUEST_REBUTTAL]:
      environment routes to named role with pending request; avoid extra judge LLM call
  else:
      corresponding frozen LLM executes the action; LLM chooses target/content
      validate, deduplicate, atomically update hypothesis/claim ledger
      recompute features, component score deltas and training reward
      active_role = Judge
  log transition on global timeline

if budget reached: obtain one forced Judge LLM verdict and score it
```

To make **all three actor policies meaningful**, a `REQUEST_SUPPORT` transition must route to Prosecutor **actor**, not call Prosecutor LLM with a hardcoded `SUPPORT`. The Prosecutor can pick `SUPPORT`, `REVISE` or `REST` subject to masks. Likewise, `REQUEST_REBUTTAL` routes to Defender actor.

At the start of the episode, Prosecutor's Top-3 LLM initialization is not an RL transition. Training the Prosecutor actor therefore requires Judge to sometimes route back to it. If the dataset/policy almost always stops after one Defender action, use training exploration/curriculum to ensure Prosecutor has nontrivial rollout coverage, and **report per-role number of policy decisions**.

**Budget and deadlock safety:** no more than 10 RL decisions in initial V1; at most 3 initial hypotheses and 2 supporting claims each; bounded expansions/new claims, e.g. max 8 active claims; one challenge and one substantive response per claim unless genuinely new evidence appears. Tune these only on train/dev. If one side rests, control returns to Judge; if no informative actions remain, force verdict.

## 6. Observation: specifically inspired by CREW

CREW's `get_obs()` builds one row per available action, with columns `Relevance, Novelty/Coverage, Historical Impact, Token Remaining, Social Usage`. Its actual Actor consumes a flattened `(4,5)` matrix. It calculates embeddings of task/local/global/draft/feedback but **does not receive raw text directly**.

For this task, keep the **per-action feature matrix**, but do not transplant irrelevant CREW metrics. Compute all features from **validated public state**, deterministic text processing, cached embeddings and online *past* statistics. No extra pre-action LLM analysis is required.

Recommended V1 matrix: `n_actions(role) × 6` (P: `3×6`, D: `4×6`, J: `3×6`), followed by a small shared-global vector for budget/turn status.

| Feature | Semantics | Suggested source / example computation |
| --- | --- | --- |
| Relevance | How relevant available supporting/contradicting text is to performing **this** action | Cosine between case embedding and relevant unresolved claim/hypothesis embeddings (bounded, avoid interpreting semantic similarity as logical truth) |
| Opportunity | How much *unprocessed eligible work* exists for that action | Normalized count of unchallenged claims / unresolved hypotheses / requests needing response |
| Evidence gap | Whether evidence needed for that action is missing or disputed | Missing exact quotes, challenged-without-response claims, validator flags; **not** arbitrary LLM self-confidence |
| Novelty | Whether the next action has room to add nonduplicate content | One minus maximum similarity to prior same-kind evidence, combined with exact normalized quote/claim dedup |
| Historical impact | How helpful this action type has been **in the past**, not in the future | EMA of observed past component-delta scores within current episode; optional frozen training-derived prior |
| Cost / budget | Whether action is affordable | Remaining turns, action-specific token usage, rolling observed call cost |

Action rows **must be action-specific**. `REVISE` relevance/opportunity refers to candidate hypothesis gaps, not merely a copy of `SUPPORT` signals. For `VERDICT`, focus on unresolved-issue count, progress plateau and budget. For `CONCEDE`, do not claim a cosine similarity score proves the hypothesis true; only represent whether substantive objections remain and how much evidence has been checked.

Initial defaults for unobserved EMA features must be neutral (not zero as a fake negative outcome), with explicit `n_observed` or validity mask. Action masking is separate from observation features: invalid logits are set to `-inf` prior to categorical sampling. `REST` should remain available to P/D, `VERDICT` always available to Judge.

### Why Actor has grounds to choose CHALLENGE vs PROPOSE_ALTERNATIVE

- `CHALLENGE` opportunity increases with grounded **existing claims** still needing scrutiny; its evidence-gap is high if current claims cite missing or weak support.
- `PROPOSE_ALTERNATIVE` opportunity increases when there are unexamined hypotheses or evidence that current claims fail to cover; avoid rewarding a label change itself.
- Neither feature can prove fallacy type or logical invalidity. LLM executor determines the target claim/label **after** Actor chooses strategy.
- Compare structural-only against embeddings-added observations in ablations; if semantic features give no gains, drop them.

## 7. Validation and anti-repetition

1. Each claim/evidence gets stable IDs and normalized quote fingerprints; same text span alone cannot generate multiple positive evidence units.
2. Deny previously performed `(role, action, claim/hypothesis, evidence fingerprint)` combinations. The **LLM-selected target** is checked after execution; invalid repeats pay a cost, and future eligibility/masks tighten.
3. Use semantic similarity **only as a candidate duplicate detector**; do not conflate logically contrasting propositions merely because their embedding similarity is high. Confirm or flag uncertain duplicates.
4. Bound `challenge_count`, `response_count`, per-hypothesis visits and overall budget.
5. Semantic novelty cannot itself imply logically correct evidence. Incorrect quotations, unsupported claims and repeated arguments must not increase state quality merely through verbosity.
6. An action can produce no valid new evidence; do not fabricate a state improvement. Record `no_op` and its cost.
7. Role LLM prompts must distinguish `CHALLENGE` (inspect weaknesses of existing claims) from `PROPOSE_ALTERNATIVE` (offer a substantiated competing fallacy) with structured, auditable outputs.

## 8. CREW-inspired reward: component-quality *deltas*

CREW computes action-conditioned quality improvements in local/global knowledge, feedback and draft. Translate this idea to a **Courtroom component delta** rather than copying its text-similarity scoring directly.

Define persistent bounded qualities for state `s`:

- `Q_local_i(s)`: **validated** unique contributions of current role; grounded evidence, nonduplicate reasoning units and substantive responses. Do not use LLM eloquence/confidence as truth.
- `Q_board(s)`: overall source-grounded, deduplicated, properly tracked claim/hypothesis ledger; a good refutation may *improve* this without increasing count.
- `Q_decision(s)`: independent frozen 8-class assessor's score for correct gold label *when computing training reward only*. Input: case + public validated ledger; the assessor never receives gold. No Judge self-confidence used.

With component scales bounded and normalized from training data:

```python
w_t = clip(0.2 + 0.6 * t / max(1, H-1), 0.2, 0.8)
progress_t = (1 - w_t) * (0.4 * delta_Q_local + 0.6 * delta_Q_board) \
             + w_t * delta_Q_decision
reward_t = 0.3 * clip(progress_t, -1, 1) \
           - 0.01 - 1e-5 * generated_tokens_t - 0.1 * invalid_action_t
if final_verdict:
    reward_t += 1 if predicted_label == gold_label else -1
```

All constants are **starting experimental values, not established optima**. Keep individual reward parts in the trace. Do not give bonuses just for CHALLENGE, REVISE, CONCEDE, REST, selecting a candidate, or reaching agreement. A wrong persuasive claim should not systematically earn positive reward; an accurate critique should be able to improve ledger quality.

**Important limitation:** weighted component-delta shaping need not preserve the optimal policy for terminal accuracy. Run these three ablations:

A. Terminal-only: `+1/-1 - costs`.
B. Potential-based: `r += gamma*Phi(s_next)-Phi(s_now)` using bounded independent-assessor log-prob of gold on training samples, with terminal potential set to zero.
C. CREW-inspired component-deltas above.

Reject a dense reward if it raises training surrogates while lowering dev macro-F1 or making decisions more verbose. For fairness, keep Judge assessor separate from Judge LLM and freeze assessor across an experiment.

## 9. RL training mechanics

- Train **three separate role-specific Actor MLPs** with IPPO first; each outputs categorical action-type logits for its role. Shared reward goal, but gradients do not update frozen LLM agents. Optionally compare centralized-critic MAPPO later.
- Implement **global-time turn-based transitions**. Example: P may act at `t=3` and again `t=7`; consecutive P actions in its own buffer are **not** adjacent global time steps. Use one global rollout timeline with active-agent masks, or correct per-agent discounting by actual `Δt` (`gamma**Δt`). Never naively run CREW's per-agent GAE as if P had acted every step.
- Store: `sample_id`, `step_id`, active role, observation, **action mask**, action, old log-prob, value, separate reward components, next observation, `terminated`, `truncated`, model/cache fingerprints, token counts and ledger revision.
- Judge `REQUEST_*` gets its future benefit through downstream return/GAE, not a fabricated immediate quality gain. Judge `VERDICT` is a terminal decision, final label produced by frozen Judge LLM.
- `terminated=True` for valid verdict; distinguish budget exhaustion, forced verdict and infrastructure failure. Do not silently discard hard/failed episodes; infrastructure errors require explicit accounting and retry policy.
- Warm-start via fixed courtroom baseline and **heuristic action demonstrations** on **train only**; imitation must be treated as initialization, not gold policy. Then on-policy PPO with exploration and multiple seeds.
- Preserve split provenance and checkpoint role-specific Actor/Critic, optimizer, feature normalization, frozen model/prompts, reward assessor and all configuration hashes.

### Data and episode sampling

`train.json` for PPO, `dev.json` for tuning, `test.json` once after freeze; all with `select_task(samples, "classification")`. Preserve paper-style context from `ModelInput` and use `src/evaluate.py` equivalent to report macro-F1 over all eight labels, overall accuracy, per-class recall/confusion, calls, tokens, mean/median steps, repeated-claim rate, early-stop rate and Top-3 recall. Use identical model/decoding budgets across comparisons.

## 10. One illustrative episode

```text
Initial context: title + parent comment + target comment
Prosecutor LLM init:
  H1 = False Dilemma       -> C1, C2
  H2 = Slippery Slope      -> C3, C4
  H3 = Hasty Generalization-> C5, C6

Defender observation: CHALLENGE has high eligible-claim opportunity and evidence gap.
Defender Actor -> CHALLENGE
Defender LLM -> chooses C2 and identifies missing exclusion of alternatives; stores rebuttal R1.

Judge observation: substantial dispute unresolved.
Judge Actor -> REQUEST_SUPPORT; env routes to Prosecutor Actor.
Prosecutor Actor -> REVISE
Prosecutor LLM -> adjusts the hypothesis support, grounding revisions in comment.

Judge observation: low remaining disagreement / new evidence and limited budget.
Judge Actor -> VERDICT
Judge LLM -> selects among all 8 labels; final reward computed privately.
```

The action choices above are **illustrative trajectories**, not hardcoded rules; an actual trained policy may choose differently. The Judge is free to choose a label outside H1–H3, including when initial Top-3 missed gold.

## 11. Suggested package boundaries

```text
courtroom_rl/
  adapters/
    case_loader.py          # thin wrapper of test_debate_agents' existing loader
    llm_roles.py            # reuse its client, schemas, retry and cache
    crew_ppo.py             # reuse CREW Actor/PPO code via compatibility adaptation
  env/
    state.py                # Hypothesis, Claim, CourtroomState
    ledger.py               # validated events, claims, evidence, dedup
    observation.py          # action-specific CREW-like feature matrix
    action_mask.py          # role and state eligibility
    courtroom_env.py        # sequential reset/step/termination
    reward.py               # per-component quality delta, terminal reward
  rl/
    policies.py             # role-specific action logits
    rollout.py              # global timeline and GAE masks
    train.py                # PPO, checkpoint, dev evaluation
  tests/
    test_gold_isolation.py
    test_top3_schema.py
    test_turn_routing.py
    test_action_mask.py
    test_claim_dedup.py
    test_reward_deltas.py
    test_global_time_gae.py
    test_forced_verdict.py
    test_cache_integrity.py
```

This is a **suggested organizational layout**; avoid recreating existing modules if direct imports/adapters work. Keep original baseline executable unmodified.

## 12. Acceptance criteria and experiment plan

- [ ] Raw Top-3 init contains exactly 3 **distinct valid labels** and grounded claims; invalid outputs invoke bounded retry/error accounting.
- [ ] No RL Actor logits correspond to any of the 8 label IDs or individual claim IDs.
- [ ] Defender `CHALLENGE` and `PROPOSE_ALTERNATIVE` lead to meaningfully distinct LLM instructions, while LLM chooses all targets.
- [ ] Judge `VERDICT` routes to Judge LLM which may select **any** of eight labels.
- [ ] Three Actor parameters are separately saved and shown to receive gradients on nonempty rollout samples.
- [ ] No hidden gold leakage in observations, role prompts, cache input or frozen assessor input.
- [ ] All invalid/repeated actions and resulting LLM calls are logged; masks prevent avoidable repeated requests.
- [ ] A no-op has zero quality-delta progress before costs; unchanged quality cannot earn positive progress per repeated step.
- [ ] PPO correctly handles gaps between actions from the same role, action masks and terminal/truncation flags.
- [ ] At budget exhaustion, a forced verdict is recorded and scored; infra errors remain distinguishable.
- [ ] Baselines: existing fixed single-charge debate, fixed Top-3 debate, random valid action policy, heuristic policy, learned policy.
- [ ] Ablations: structural vs semantic observation; terminal-only vs potential-based vs CREW-inspired dense reward; varying budgets.
- [ ] Evaluate accuracy, macro-F1, tokens, API calls, number of steps, cost-quality frontier, Top-3 recall, per-role decision coverage and duplicate rate with multiple seeds.

## 13. Exact source links

- Courtroom branch: https://github.com/HuyL13/test_debate_agents/tree/feat/adversarial-dialectical-debate
- Courtroom action execution: https://github.com/HuyL13/test_debate_agents/blob/feat/adversarial-dialectical-debate/src/adversarial_debate.py
- Courtroom role prompts: https://github.com/HuyL13/test_debate_agents/blob/feat/adversarial-dialectical-debate/src/adversarial_prompts.py
- Courtroom data loader: https://github.com/HuyL13/test_debate_agents/blob/feat/adversarial-dialectical-debate/src/data/loader.py
- CREW environment: https://github.com/YenPBao/CREW-Collaborative-MARL/blob/main/src/rl_env/rwg_env.py
- CREW PPO trainer: https://github.com/YenPBao/CREW-Collaborative-MARL/blob/main/src/train_self_supervised.py
- CREW buffer: https://github.com/YenPBao/CREW-Collaborative-MARL/blob/main/src/training/ippo_trainer.py
