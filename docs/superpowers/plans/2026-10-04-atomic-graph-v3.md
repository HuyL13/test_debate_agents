# Atomic graph semantic repair implementation plan

**Goal:** Implement the supplied semantic repair guide with reproducible v2/v3 comparison and no classification.

**Architecture:** Deterministic sentence spans; node extraction and audit; locked-node relation extraction and audit; deterministic canonical rendering. Models provide verbatim quotes, and Python resolves character offsets. Bounded semantic verification is enabled for the smoke run and logs issues outside final graphs.

**Spec:** `C:/Users/yoga/Downloads/atomic_graph_semantic_repair_implementation_guide.md` (user-selected implementation requirements).

**Constraints:** Preserve v2 outputs/schema; unchanged 10 discourse relations, SUPPORT only; no gold labels; no forced connectivity; new outputs per version/seed; sentence-relative Unicode character offsets with exclusive end.

- [x] Contract and provenance: add schema v3, staged schemas, deterministic segmentation/quote resolution and ID/span/scope/coreference/edge validators; prove failures and positive cases.
- [x] Extraction: contrastive node/relation prompts, mandatory locked-node interface, optional semantic verifier enabled in v3 config, bounded feedback repairs and trace.
- [x] Execution: v3 dispatch in existing CLI; fresh output namespace; QA summaries and prompt/config snapshots, deterministic linearization, errors outside graphs.
- [ ] Verification: regressions for original failure classes, runner tests, full suite and code review; run original ten and new seed with no gold label in prompts; compare source-grounded review observations rather than edge counts as quality.

Tests run before implementation and again after each meaningful change. The existing unrelated dirty files are preserved. No automatic push or merge is part of this change.

Verification progress: full suite passes; code review completed; original ten attempted and manually reviewed, with three automatically accepted graphs held as drafts. `outputs/atomic_graph_v3_seed42_r3/review_notes.md` documents source-based outcomes and prompt versions. New hold-out is blocked by automatic outbound approval review until the user authorizes the seed-43 payload. The latest review-ontology prompt correction is tested but not experimentally rerun.
