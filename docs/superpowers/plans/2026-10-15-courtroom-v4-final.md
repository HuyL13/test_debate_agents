# Courtroom V4 final implementation

User authorized full implementation after the reward audit. Existing V3 stays
reproducible. No claim of measured accuracy superiority before new training.

## Decision grounded in experiments

- Terminal +/-1 + original step/output-token/invalid costs is the production
  objective. Remove unvalidated CREW proxy shaping in V4, and do not replace it
  with the failed full-history TF-IDF candidate. Costs remain .01/step,
  .00001/output token, .1/invalid, call cost0, gamma .99.
- Full public argument content, including CONCEDE rationale, reaches Judge.
- Frozen pinned BGE-base-en-v1.5, outside PPO, provides768-dimensional source,
  hypothesis/claim and history embeddings. Labels/status are explicit features.
- Per-role actor chooses action + conditional existing target. LLM writes
  grounded arguments, chooses new labels where appropriate, and final verdict.
- Source/target attention128 dimensions,4heads, no dropout, separate local critics.
- Keep global-timeline GAE; do not duplicate terminal or macro rewards.
- Train official3168. Dev exact dialectical66, never call it fresh held-out test.

## Fixed interfaces for independent implementation tasks

Package src/courtroom_rl/action_centric_v4.

### Environment/executor/observation

CourtroomEnv subclasses V3. step(action,target=None). legal_actions() and
legal_targets(action) return action list and target ID list (None for no-target).
SUPPORT/CHALLENGE/CONCEDE: claim IDs; REVISE:hypothesis IDs;
REQUEST_SUPPORT/REQUEST_REBUTTAL: claim IDs; REST/VERDICT/PROPOSE_ALTERNATIVE:None.
Requests bind recipient scope to the selected target. LLM cannot substitute
another target: schema enum/guide and validation restrict it. Invalid actor
targets fail before API calls. Recipient can respond substantively or decline;
CONCEDE is a response with its rationale retained, not ground-truth declaration.
Recorded trace contains selected target, joint/action/target logprobs, masks,
full usage/rewards and replayable state hash. Terminal reward is recorded once.

Observation encode(env) dict:
- source:float32[768]
- objects:float32[16,768], object_features:float32[16,34]
- object_mask:bool[16], ids:list of16 strings/None, hypotheses first then claims
- history:float32[10,768], history_mask:bool[10]
- global:float32[12]

Object feature34:label8, author3, status12, kind3, type2, bounded publicstats6.
Statuses:OPEN,DISPUTED,RESPONDED,CONCEDED,UNRESOLVED,CLOSED,ACTIVE,CHALLENGED,
SUPPORTED,WEAKENED,REJECTED,RESOLVED. Public source/evidence/reasoning only;
gold/private probabilities/rewards never enter encode or LLM prompts.
Constants TEXT_DIM=768,MAX_OBJECTS=16,MAX_HISTORY=10,OBJECT_FEATURE_DIM=34,
GLOBAL_DIM=12; ROLE_ACTIONS reused V3. Offline fixture vectors may be padded
from explicitly-marked128-dimensional FixtureEncoder, never a live fallback.
OBS_DIMS exports JSON-serializable structured feature description for manifest.

LLMExecutor(client,input_estimator=None), FixtureExecutor compatible V3 init;
execute reads actor_target set by env. Shared dialogue_view includes source,
ledger and argument_events stripped of rewards/private/debug/runtime data.
replay(row) executes step(event.action,event.actor_target/target) with recorded
executions and verifies action/target masks + state hashes.

### Policies/trainer

PPOTrainer(seed,lr,gamma,lam,clip,epochs,entropy,device) compatible save/load/update,
rollout(env,deterministic=False,progress=None,demonstration=False),imitate().
RolePolicies.sample(role,obs,legal,targets,deterministic) returns action,target,
logprob (joint),action_logprob,target_logprob. evaluate returns joint logprob,
entropy. Action logprob + conditional target logprob defines PPO ratio.
targets is {action:list of legal target IDs/None}; IDs map to obs.ids.
For no-target action target isNone and conditional logprob is0. Normalize
advantages per role after global GAE. Critics receive structured observations.
heuristic(env,fixed=False) returns (action,target), using public eligibility only.
Checkpoint guards architecture/source/config/data/dev/model/device; CPU/CUDA RNG
and Adam state roundtrip. Never restore V3 weights into incompatible V4 network.

## Tasks and acceptance

1. Environment, grounded executor, full dialogue, observations, replay + tests.
2. Attention policy/critic, joint PPO/GAE, save/load/fixture tests.
3. Runner/CLI/config/bootstrap/Kaggle docs and diagnostic66 wiring.
4. Full suite, information-invariance controls, fixture end-to-end resume/replay,
   live bounded pilot with realBGE/API and eval on66; report actual metrics and
   limits, no accuracy guarantees or untested assessor. Review before delivery.
