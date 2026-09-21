# Unified Adjudication Design

## Objective

Improve the original three-perspective CoCoLoFa pipeline without replacing its
FORM (`structure`), FUNCTION (`goal`), and FAILURE (`counterargument`) motivation.
Remove destructive pairwise elimination and make the final decision compare all
supported and contested readings, including an explicit non-fallacious reading.

## Trace Motivation

- Multi-agent detection trails single-LLM detection: 76.44% versus 79.70%
  accuracy, primarily because false positives are 125 versus 77.
- Counterargument proposes a fallacy for 194 of 317 negative samples and supports
  the final wrong candidate in 106 of 125 false positives.
- In classification, resolver directly eliminates the gold label in 22 samples;
  the downstream arbiter recovers none of them.
- On detection samples with one surviving candidate, the arbiter rejects 98:
  63 are correct rejections and 35 are false negatives. Directly accepting every
  singleton would reduce accuracy to 72.93% and increase FPR to 59.31%.
- Classification errors concentrate in Hasty Generalization overprediction and
  confusion among Hasty Generalization, Slippery Slope, False Dilemma, and Appeal
  to Worse Problems.

## Architecture

Each initial analyst independently returns a verdict, at most one candidate,
target evidence, the candidate's mandatory condition, whether that condition is
satisfied, and the strongest reason against its own conclusion. The
counterargument analyst explicitly compares a strongest objection with a
strongest defense so that formulating an objection does not force a positive
label.

Application code validates report consistency but does not semantically delete a
candidate. It builds a deduplicated candidate dossier containing every source's
support and opposition. A single final comparative adjudicator replaces both the
pairwise resolver and the final arbiter.

Detection always calls the final adjudicator. Its choice set contains every
proposed candidate plus `Non-Fallacious`. If no analyst proposes a candidate, the
adjudicator enters bounded recovery over all eight labels plus
`Non-Fallacious`; a positive recovery requires a named label and concrete
mandatory condition.

Classification normally compares the union of at most three candidates. A sole
candidate may be returned deterministically only when at least one report marks
its mandatory condition satisfied and no report contests it. Otherwise the
adjudicator runs. If no candidate exists, classification recovery uses the full
eight-label set.

## Role Contracts

All reports include:

```yaml
verdict: Fallacious | Non-Fallacious
candidate: label | null
mandatory_condition: string | null
condition_satisfied: boolean
opposing_reason: string
evidence_ids: []
```

Detection requires `candidate=null` for a negative verdict and a candidate for a
positive verdict. Classification permits abstention in an initial report but the
final prediction must be one of the eight labels.

Role-specific fields remain focused:

- structure: `structure_type`, instantiated `slots`, premise/conclusion/link;
- goal: conclusion, supporting reason, support relation, discourse ownership;
- counterargument: challenged inference, strongest objection, strongest defense,
  and which side wins.

## Candidate Dossiers

Each candidate dossier contains all reports that proposed it and all reports
that opposed a positive interpretation. Reports are marked `supported`,
`contested`, or `unsupported`; these states are evidence for adjudication, not
destructive filters. Candidate conditions and evidence never move between labels.

## Final Adjudication

The final call receives raw TARGET, all reports, dossiers, the explicit
non-fallacious hypothesis for detection, and the allowed labels. It may reject
all fallacy candidates in detection. It returns one verdict, one candidate or
null, decisive target evidence, the decisive condition, and a rejection reason
for every competing candidate.

The prompt includes contrastive tests:

- Hasty Generalization requires sample/cases to a broader population;
- Slippery Slope requires an escalation or consequence progression;
- False Dilemma requires alternatives and an exhaustiveness commitment;
- Appeal to Worse Problems requires dismissal, downplaying, or deprioritization;
- Appeal to Authority requires authority/status/opinion to do justificatory work.

Modality, negation, quotation, criticism, and parent/target ownership remain
mandatory checks.

## Calls And Artifacts

The normal path uses four calls: three independent analysts and one final
adjudicator. No resolver calls remain. Existing trace, CSV, resume, cache,
rate-limit, and metric formats stay compatible where practical; traces record
initial reports, dossiers, final adjudication, and aggregate call statistics.

## Verification

Use TDD for schemas, dossier construction, routing, engine behavior, and runner
artifacts. Run the existing test suite, then smoke-test the real API on detection
and classification. Full benchmark evaluation continues to use the repository's
existing metrics only.
