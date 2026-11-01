# Proposal 1 — aligned argument classification

This implements Proposal 1 from the November 1 review. Select it explicitly with
`engine.defender_policy: proposal_1`. Existing profiles and detection keep their
existing behavior. The working-directory Defender v1/v2 changes are preserved in
a separate parent commit, not mixed into this implementation commit.

## Behavior

- `src/aligned_classification.py` supplies one authoritative definition of all
  eight classes to Prosecutor, Defender and Arbiter. These definitions replace
  the historical cue-first guidance for this profile, independent of the legacy
  `use_patterns` setting. A warning about bad consequences alone is not SS;
  action/inaction is not the FD/SS distinction; implicit exclusion is permitted
  only when licensed by text; Worse Problems concerns may be related.
- The Prosecutor commits premise/conclusion evidence and the disputed inference,
  including intermediate defective steps. Candidate and runner-up use identical
  assessment fields. A forced runner-up may admit missing conditions and have
  no quote; it must not invent evidence just to appear viable.
- Defender separates `condition_status` from `inference_role`. Both assessments
  share the same schema. Defer identifies a specific unresolved commitment;
  challenge requires a supported alternative, a candidate objection and a
  concrete structural difference. The adapter preserves raw and effective
  decisions and records gate reasons without claiming semantic validation.
- All quoted evidence is an exact, case-sensitive contiguous TARGET substring.
  Implicit premises/conclusions need an explained, textually licensed warrant.
  No ellipses, invented quotes, source-status locking, or regex semantic vetoes.
- Arbiter sees anonymous dossiers with the inference, assessments, objections
  and comparison, alongside the full target/context. Its dynamic prompt includes
  the exact output schema even when provider structured output is disabled.
  It must assess each offered option and explain both the selection and the
  rejected option. It can record `unresolved` or `both_unsupported` while making
  a forced benchmark choice.
- To isolate Proposal 1 from the game mechanism, the conservative legacy policy
  remains: one adjudication for uncontested cases, two swapped adjudications for
  challenges; the alternative wins only with two supported selections. Other
  outcomes retain the candidate. Raw verdicts/uncertainty remain in the trace.
  Aggregate confidence is an uncalibrated conservative diagnostic, not a
  posterior or the mean of confidence in different labels.

## Run

From the repository root:

```bash
python -m src.run_classification --config configs/classification.adversarial.proposal-1.marketplace.yaml --mock --limit 3 --output outputs/proposal-1-mock
python -m src.run_classification --config configs/classification.adversarial.proposal-1.marketplace.yaml --limit 100
```

The second command makes paid API calls and is not run as part of implementation.
Default data is dev. Prepare the normal CoCoLoFa data first and configure
`MARKET_API_KEY` for a live run. Mock results verify contracts, not accuracy.
Source/config changes affect the existing experiment identity: use a new output
directory after changes; resume cannot mix profiles or versions.

## Paired replay

The existing evaluator now accepts the versioned aligned Prosecutor report:

```bash
python scripts/evaluate_defender.py snapshot --config configs/classification.adversarial.proposal-1.marketplace.yaml --predictions outputs/proposal-1-aligned-dev/predictions.jsonl --output outputs/proposal-1-prosecutor-snapshot.json
python scripts/evaluate_defender.py run --config configs/classification.adversarial.proposal-1.marketplace.yaml --snapshot outputs/proposal-1-prosecutor-snapshot.json --output outputs/proposal-1-replay
```

Snapshot/input/context hashes are checked before API calls. Old v1/v2 reports
lack the new inferential contract and are rejected before a proposal run;
there is no silent reconstruction or live Prosecutor fallback. Proposal 2 uses
the same Prosecutor contract, allowing exact paired comparisons between the two
proposals. Changed Prosecutor prompts require a separate experiment against old
profiles; do not claim the entire change is a Defender-only effect.

## Validation and limits

Run `python -m pytest -q`. Tests exercise evidence provenance, implicit warrant
contracts, symmetric assessments, actual request payloads, swapped adjudication,
fallback policy, exact snapshot replay, no live Prosecutor calls during replay,
mock end-to-end execution, and resume/version rejection.

No live benchmark, prompt-accuracy gain, equilibrium, or semantic correctness is
claimed. Review on dev, include pass/defer cases, measure harmful and beneficial
flips and candidate coverage, and treat the previously inspected test set as
regression rather than an untouched holdout.
