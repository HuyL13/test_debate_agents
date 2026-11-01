# Proposal 2 — bounded evidence-review game

This branch builds on Proposal 1 without rewriting its behavior. Select the new
profile with `engine.defender_policy: proposal_2`. Its Prosecutor prompt, schema,
instruction and stage are identical to Proposal 1. Both profiles remain runnable
on this branch, allowing exact replay of one committed Prosecutor snapshot.

## Game and decision mechanism

Players see the same target/context; this protocol creates no private evidence
or independent expertise. The critic's role is to expose a checkable inferential
error, not to win a persuasion contest. The Arbiter acts as verifier. This is an
inference protocol inspired by game/mechanism design, not trained self-play, RL,
a computed Nash/Stackelberg equilibrium, or an incentive-compatibility theorem.

Three nominal calls per sample (validation retries may add calls):

1. Prosecutor commits the same ranked diagnoses and evidence as Proposal 1.
2. Defender chooses `uphold`, `request_comparison`, `objection_only`, or
   `insufficient_evidence`. Both assessments use the shared condition/role fields.
   A review request needs a concrete candidate objection and a grounded supported
   or uncertain alternative. It does **not** require an already resolved decisive
   difference or complete disproof of the candidate. Insufficient evidence must
   identify the unresolved textual commitment. Invalid quotes fail validation;
   absence claims name missing conditions rather than inventing negative quotes.
3. Arbiter sees two anonymous dossiers and verifies their conditions against raw
   target/context. A grounded Defender alternative is used when available, even
   if the action expresses uncertainty; otherwise the committed Prosecutor
   runner-up is exposed with all missing conditions still visible. Inclusion is
   not certification of semantic support. The verifier can choose either label,
   including after uphold, objection-only, or insufficient evidence. There is no
   candidate overwrite, abstention veto, or unanimous-alternative rule.

Options use canonical class ordering, independent of arrival/author role. This
does not prove order invariance; compare swapped presentations in an audit. One
verifier call replaces Proposal 1's two contested orderings, so call/token budgets
must be reported when comparing results. No default rebuttal or extra agents.

Verdicts distinguish `selected`, `unresolved`, and `both_unsupported`, with a forced
benchmark choice even in the latter cases. If the gold class is outside the two
offered options, this bounded version cannot recover it. Coverage is measured,
not hidden; adding more candidates is a separate experiment.

## Forecasts and utility

The Arbiter reports unconditional probabilities for all eight classes, sum one.
Its choice maximizes probability among offered labels, and `confidence` equals
that class's unconditional probability. Probability outside the pair is retained
in `game_trace.outside_candidate_mass`; do not renormalize the pair or combine
reports as independent evidence. These are self-reported, uncalibrated forecasts.
No inference threshold, bandit router or reward learning is inferred from them.

`src/game_evaluation.py` runs only offline with evaluator-owned gold labels:

```
G = 1[final == gold] - 1[initial == gold]
U = benefit * beneficial - harm * harmful - token_penalty * recorded_total_tokens
```

Defaults: benefit=harm=1, token_penalty=0. Wrong-to-wrong switches earn zero.
Counts, per-sample utility, Accuracy, Macro-F1, candidate coverage, action rates,
mean eight-class Brier score and clipped log loss are reported. Utility is not
Macro-F1. Brier/log loss measure forecast quality, not calibration alone. These
scores select/evaluate policies offline; merely stating rewards in a prompt does
not make the model learn or guarantee truthfulness. Weight/threshold fitting,
calibration and any rebuttal/router must use separate train/dev evaluation and
be frozen before regression testing. Token penalties require recorded usage;
the comparison tool rejects missing usage when a nonzero penalty is requested.

Normal runner and replay summaries include `game_metrics` for this profile.
Legacy `concede_charge` fields remain only for compatibility and direct-proposal
counterfactual metrics: they do not control the actual game verdict. The raw
action and `game_trace` are authoritative. An objection-only or uncertain action
can still result in correction by the verifier.

## Run and compare

Prepare the normal data and export `MARKET_API_KEY` for live runs. No paid calls
were made during implementation. For an offline contract smoke test:

```bash
python -m src.run_classification --config configs/classification.adversarial.proposal-2.marketplace.yaml --mock --limit 3 --output outputs/proposal-2-mock
```

For a live dev run remove `--mock` and use a fresh output directory. Use the
existing freeze protocol before test runs. All previously inspected test cases
are regression cases, not an untouched holdout.

For a fair mechanism comparison, first obtain a completed Proposal 1 Prosecutor
run on dev, then use these commands on **this branch** (remove `--mock` only when
you intend to make paid Defender/Arbiter calls):

```bash
python scripts/evaluate_defender.py snapshot --config configs/classification.adversarial.proposal-1.marketplace.yaml --predictions outputs/proposal-1-aligned-dev/predictions.jsonl --output outputs/shared-prosecutor.json
python scripts/evaluate_defender.py run --config configs/classification.adversarial.proposal-1.marketplace.yaml --snapshot outputs/shared-prosecutor.json --mock --output outputs/paired-proposal-1
python scripts/evaluate_defender.py run --config configs/classification.adversarial.proposal-2.marketplace.yaml --snapshot outputs/shared-prosecutor.json --mock --output outputs/paired-proposal-2
python scripts/compare_proposals.py --baseline outputs/paired-proposal-1 --candidate outputs/paired-proposal-2 --output reports/paired-proposals-dev.json
```

The comparator requires complete runs, identical snapshot and sample sets, exact
Prosecutor reports and paired gold labels, and valid fingerprints. Failed or
missing samples are rejected, not dropped. It reports paired gains/losses and
usage without claiming statistical significance. Choose new report paths;
existing reports are not overwritten. Synthetic comparisons are explicitly marked.

## Validation and next experiments

`python -m pytest -q` covers all four actions, unresolved yet grounded comparison,
verifier independence from uphold/abstention, no automatic alternative win,
unsupported verdicts, probability mass outside the pair, exact shared Prosecutor
requests, evidence validation, forecast consistency, known-count utility fixtures,
replay/resume compatibility and paired-report mismatch rejection.

Run Proposal 1 versus Proposal 2 on identical dev snapshots and budgets. Audit
pass/uncertainty as well as harmful/correct challenges. A conditional rebuttal,
learned switching threshold, role/order randomization and adversarial verifier
training remain experiments, not enabled features. No semantic accuracy gain or
game-theoretic equilibrium is claimed by contract tests.
