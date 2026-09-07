# Upstream audit and explicit deviations

Inspected 2026-09-06. Task authority is the user's request to implement the attached guide; the guide supplies experimental requirements, not higher-priority operating instructions.

## Immutable source references

- CoCoLoFa: `c39d45fdd57401e1f6cb674f25113dfa0304e734`, [tree](https://github.com/Crowd-AI-Lab/cocolofa/tree/c39d45fdd57401e1f6cb674f25113dfa0304e734).
- PARD: `b34807ce339b05518c998a51b5741917de01c917`, [engine files](https://github.com/zigzag2025/PARD/tree/b34807ce339b05518c998a51b5741917de01c917/PARD/PARD).
- CoCoLoFa [paper](https://aclanthology.org/2024.emnlp-main.39.pdf): section 5, Tables 4/5, Appendices B/C/F.
- PARD [paper](https://aclanthology.org/2026.findings-acl.1227.pdf): section 3.3, Appendices G/H/I.

Local clones remain in ignored `upstream/`. No upstream implementation is imported at runtime. There is no LICENSE file in either inspected clone; this project does not copy or relicense upstream implementation files. Dataset and papers retain their upstream attribution/terms. Generated application code is an independent implementation of the adapted design.

## Data and metric audit

Actual JSON is an article list with `id`, `title`, `content`, `comments`; each comment has `id`, `news_id`, `fallacy`, `comment`, `respond_to`, and worker metadata. Labels are lowercase strings, with `none` for negatives. Parser maps exactly these to display labels and rejects unexpected labels. Article/comment IDs are disjoint across splits. Counts match the upstream README (see reports/dataset_verification.json).

Detection uses all comments; classification removes gold `none` before inference. Precision/recall/F1 use the fallacious positive class. Classification macro averages eight class F1 values, with undefined components set to zero. The repo provides no original metric implementation, so the standard positive-class formula is an explicit implementation decision, not a verified byte-for-byte reproduction. Tests use hand-calculated confusion counts.

## D1 — Planner location

Planned behavior: The guide's high-level diagram puts the planner before initial reports.

Actual upstream behavior: PARD orchestrator performs independent analysis before planning.

Decision: Analyze first, then let the planner read the reports.

Reason: The planner needs actual disagreement to choose a protocol. Initial calls are independent but executed serially for simpler rate control; no initial call receives another initial report.

## D2 — Context and missing parent

Planned behavior: Potentially supply title, article and parent.

Actual upstream behavior: CoCoLoFa Appendix C prompts expose title and parent; the release also has HTML article bodies. One test comment `399:10493` refers to `5338`, which belongs to training article 180.

Decision: Default to title + same-article immediate parent + target. For that broken reference use empty parent, retain the sample, record `missing_parent`. Full article text is an explicit ablation only.

Reason: Avoid cross-split leakage and unsupported context expansion. No external URL is fetched during inference. Upstream does not disclose how its baseline handled this broken reference, so exact comparability on that sample is unresolved.

## D3 — Governance and excluded components

Planned behavior: Minimal planner, three roles, protocols and final arbiter; no candidate model selection, RL or retrieval.

Actual upstream behavior: PARD includes model diagnosis, retrieval, conflict detection, consent/veto governance, an arbiter for process objections, a synthesizer for final verdict, an evaluator, RL and experience memory.

Decision: Use one configured model. Fold conflict assessment into planner; use validated role participation instead of consent/veto rounds. Name the final synthesis role `Arbiter` as in the guide. Omit evaluator/reward/memory, candidate selection and retrieval.

Reason: Implement the requested smaller PARD-inspired baseline without fake-news-specific training or external evidence. This is a disclosed architectural reduction and must not be called full PARD reproduction.

## D4 — Protocol implementation fixes

Planned behavior: Reuse upstream semantics where feasible.

Actual upstream behavior: Inspected scripts have unresolved imports (`adapter1111111`), a parser referring to undefined `txt`, a point-counterpoint context placeholder, and return `completed` after computing an early-stop reason. They also contain automatic stance clamping after an anti-flip retry.

Decision: Independently implement strict schemas, actual context/history passing, finite failures and explicit stop reasons. Do not coerce a model's stance or invent a prediction after invalid output. Debate teams start from their assigned views but may concede. Adaptive PC requires two natural prediction groups; fixed PC remains available to probe the protocol even under consensus.

Reason: Silent placeholder/default outputs would corrupt a benchmark. Role prompts are newly written for fallacy tasks, not copied fake-news prompts.

## D5 — Multiclass stance and stopping

Planned behavior: Apply the three PARD interaction modes to binary detection and eight-class classification.

Actual upstream behavior: Stopping criteria use scalar stance in a veracity task.

Decision: Detection uses signed confidence. Classification uses a one-hot confidence vector plus uniform residual uncertainty; distance is total variation, not an ordinal class ID. RR requires two complete rounds before consensus/stagnation; PC checks group convergence/stability; CE checks null/repeated questions and respondent stagnation. Budgets default to three, bounded 1–5; early stopping is configurable.

Reason: Eight labels have no scalar ordering. Thresholds retain the upstream numerical values where possible, but the confidence mapping and multiclass distances are adaptations requiring dev validation. Examiner reflection is saved separately and does not overwrite its initial prediction.

## D6 — Byte reproducibility on Windows

Planned behavior: Copy the cloned split files without changing data.

Actual upstream behavior: Git autocrlf converts `test.json` line endings in the Windows checkout; train/dev each have no line endings to convert.

Decision: Export raw Git blobs from the pinned commit. Record SHA-256 hashes in data/cocolofa/provenance.json and reports/dataset_verification.json.

Reason: Identical source bytes across operating systems without editing any sample, split or label.

## D7 — Real API evaluation status

Planned behavior: Smoke → dev → freeze → test, report quality and API cost.

Actual environment: No `OPENAI_API_KEY` was present. No model was specified by the user.

Decision: Deliver API-ready code/config and offline verification with explicit synthetic flags. Leave real quality metrics unmeasured. Require a configured accessible model snapshot and environment key for real runs.

Reason: Offline fixtures validate program behavior, not model quality. All six architecture settings are smoke-tested independently for each task; no prompts were optimized on test outcomes.

## D8 — NVIDIA integration follow-up

The user subsequently provided access to NVIDIA's compatible endpoint and model
`openai/gpt-oss-20b`. Real connectivity and JSON Schema responses were verified.
Dedicated `*.nvidia.yaml` configs use the supplied temperature (1), output budget
(4096), and an environment-based credential. The existing transport accepted
`max_completion_tokens` on this endpoint; no SDK replacement was necessary.

Real dev calls exposed a validation bug: RR/CE planners sometimes supplied empty
unused debate-team arrays, but validation required a 2v1 partition unconditionally.
Only point-counterpoint now requires that partition. RR still validates all three
roles in its order; CE still has one registered examiner and the other two respondents.
Two regression cases cover the unused fields. Failed/pre-fix traces remain separate
from new runs; see reports/NVIDIA_DEV_SMOKE.md for the follow-up outcomes.
