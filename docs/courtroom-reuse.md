# Courtroom integration inventory

Approved spec: `D:/Downloads/courtroom_marl_design.md`. Implementation uses
the local checkout, preserving existing uncommitted work and baseline outputs.
Pinned upstream SHAs and licenses: `src/courtroom_rl/vendor/sources.json`.

| Feature | Existing implementation | Integration |
|---|---|---|
| Dataset/context | local `src/data/loader.py`, upstream `src/data/loader.py` | local raw loader unchanged for audit; upstream loader reused unchanged for its existing flat-record support; contexts agree in regression tests |
| Labels | local `src/labels.py` | reuse unchanged |
| API/retries/cache/validation | local `src/llm/client.py`, `openai_client.py`, `config.py` | reuse; accounting transport wrapper measures every physical attempt |
| Metrics/serialization | local `src/evaluate.py::score`, `src/io_utils.py` | reuse; wrapper reports failure coverage separately |
| Fixed courtroom | baseline `src/adversarial_debate.py::execute` | vendor unchanged except relative schema import |
| Prompts/patterns | baseline `src/adversarial_prompts.py`, `fallacy_patterns.py` | fixed baseline retains original prompts; RL reuses common grounding rules and pattern definitions through `prompts.py`, with one action schema/example and no competing baseline output instructions |
| Baseline schemas | baseline `src/adversarial_schemas.py` | reuse; relative import of upstream quote normalization helper |
| Evidence selection | local `src/evidence.py::resolve_evidence`, `target_passages` | reuse unchanged; courtroom adapter preserves ordinary sentences, adds T/P/H namespaces and exact offsets, uses existing splitter for very long sentences |
| Actor/critic | CREW `src/networks/{actor,critic}.py` | vendor unchanged; role-specific instances and hierarchical masked heads |
| GAE | CREW `src/training/ippo_trainer.py` | adapted backward recurrence on global timeline; original per-agent buffer loses intervening steps |
| PPO | CREW `src/train_self_supervised.py::_update_policy` | adapt clipping, normalized advantages, entropy, MSE; separate role actors and centralized critic |
| Environment | CREW `src/rl_env/rwg_env.py` | interface/accounting inspiration only; paper workspace, simultaneous dispatch and similarity reward incompatible |
| Courtroom state/ledger/masks | neither repository | new: claim lifecycle, grounding, budgets, requests, dedup and sequential routing |
| Observation/target head | neither repository | new: fixed deterministic text features and target masks; no downloaded encoder required |
| Replay/runner | local IO and LLM framework | new orchestration only; single command supports smoke/evaluate/train/replay |

No repeated similarity reward or self-reported confidence shaping. No gold in
state, actor/critic features or prompts. V1 uses compact frozen hashed text
features, not pretrained semantic embeddings; semantic similarity is diagnostic,
not grounds to reject distinct propositions. Vendored baseline schemas/validators
remain unchanged. `fixed` now adapts quote fields to evidence IDs on the wire,
then restores original reports for the existing pipeline/validators.
`fixed-original` runs the original free-text quote contract for controlled comparisons.

The baseline upstream has no LICENSE file. Attribution is preserved in the
source manifest; do not treat its code as MIT or publish it under a new license.

Data: train 3168, dev 927, test 481. All classification file hashes match recorded
provenance. Raw test JSON hash differs, but parsed JSON equals the exact pinned
Git object at c39d45fdd57401e1f6cb674f25113dfa0304e734; classification outputs from
the current loader match the pinned flat test exactly. The runner consumes
verified flat data and refuses unexpected hash changes rather than rewriting it.
# Action-centric V3 adapters

V3 lives in `src/courtroom_rl/action_centric` and preserves the existing baseline
and V2 modules. New adapters are necessary because V2 couples actions to RL-selected
labels/claim IDs and has a different state/observation space. V3 directly imports
the existing data/provenance loader, evidence resolver, schemas, API/retries/cache,
accounting transport, metrics, hash/serialization, frozen assessor, global-time GAE,
CREW Actor/Critic and checkpoint save/load. Its private reward subclasses the
existing component engine to interpret hypothesis-linked claim kinds and gate
wrong-label SUPPORT credit. Its prompt adapter retains substantive baseline role
behavior and taxonomy while removing incompatible one-pass output contracts.
V3 state/transactional ledger, action-feature rows and orchestration cannot be
reused unchanged from V2 because semantics, policy dimensions and paid verdict
requirements differ. They implement only that compatibility boundary.

