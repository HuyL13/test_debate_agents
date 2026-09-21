# Anchor-and-Challenge Multi-Agent Design

## Objective

Redesign the CoCoLoFa multi-agent flow so that it evaluates each target from
genuinely different perspectives, conducts targeted debate over concrete
disagreements, and improves on the single-LLM baseline without turning every
sample into an unconstrained search for a fallacy label.

The method must support both original tasks:

- detection: `Fallacious` or `Non-Fallacious` over all test comments;
- classification: one of the eight CoCoLoFa labels over gold-positive comments.

## Motivation And Trace Evidence

The current agents are not sufficiently independent. They use the same model,
context, and label definitions, and all are oriented toward proposing a fallacy.
The final arbiter is consequently framed by fallacy candidates rather than by a
balanced comparison between fallacious and non-fallacious interpretations.

Observed test-trace evidence:

- single-LLM detection: 79.70% accuracy and 83.02% positive-class F1;
- current multi-agent detection: 76.44% accuracy and 81.64% F1;
- single-LLM classification: 86.28% accuracy and 86.91% macro-F1;
- current multi-agent classification: 81.70% accuracy and 82.62% macro-F1;
- the current counterargument analyst proposes a fallacy for 194 of 317
  detection-negative samples;
- the correct subtype appears in an initial report for 398 of 481 positive
  detection samples, but viability, conflict resolution, and adjudication remove
  or reject 43 of those correct candidates;
- in all 70 cases where the single detector is correctly negative and the current
  multi-agent detector is positive, at least one candidate is proposed and the
  arbiter accepts one;
- a post-hoc structure-only diagnostic reaches 80.20% detection accuracy and
  83.26% F1. This is diagnostic evidence, not a valid test result for model
  selection.

The redesign therefore targets candidate inflation, correlated perspectives,
asymmetric adjudication, and destructive pruning. It does not increase the
number of candidates indiscriminately.

## Method Overview

The new flow is Anchor-and-Challenge deliberation:

1. A direct anchor makes the same zero-shot judgment as the single-LLM baseline.
2. A structural verifier tests whether the required inferential structure exists.
3. A contextual critic constructs the strongest defensible alternative reading.
4. Deterministic routing identifies concrete disagreements among their claims.
5. A targeted debate call addresses only those disagreements.
6. A symmetric judge compares explicit positive and negative hypotheses.
7. A deterministic contract verifier rejects internally inconsistent output; it
   does not make another semantic classification call.

Every semantic stage receives the raw target text. Reports contain explicit
evidence spans and compact claims, not hidden chain-of-thought.

## Perspectives

### Direct Anchor

The anchor preserves the strongest existing baseline. For detection it returns a
binary verdict and, only when positive, one primary fallacy hypothesis. For
classification it returns one primary label and may return one alternative only
when a named ambiguity condition holds.

Required output:

```yaml
verdict: Fallacious | Non-Fallacious
primary_candidate: label | null
alternative_candidate: label | null
evidence_spans: []
decision_reason: string
ambiguity: string | null
```

Detection requires `primary_candidate=null` for `Non-Fallacious` and forbids an
alternative. Classification requires a primary candidate. An alternative must be
distinct and justified by `ambiguity`.

### Structural Verifier

The structural verifier does not perform free-form classification. It evaluates
the anchor candidate and may name one replacement candidate only when the raw
target clearly instantiates a different mandatory structure.

Required output:

```yaml
tested_candidate: label | null
premise: string | null
conclusion: string | null
inferential_link: string | null
mandatory_condition: string
condition_satisfied: boolean
replacement_candidate: label | null
evidence_spans: []
decision_reason: string
```

A positive structural judgment requires concrete premise, conclusion, link, and
target-only evidence. Keywords and topic similarity are insufficient.

### Contextual Critic

The contextual critic builds the strongest charitable interpretation of the
target and tests discourse ownership. It must distinguish an asserted fallacy
from a quotation, question, report, criticism, hypothetical, or response to the
parent comment.

Required output:

```yaml
speech_act: assertion | question | quotation | criticism | hypothetical | other
fallacy_owned_by_target: boolean
charitable_interpretation: string
missing_condition: string | null
recommended_verdict: Fallacious | Non-Fallacious
candidate: label | null
evidence_spans: []
decision_reason: string
```

This role replaces the current counterargument analyst. Its objective is not to
find a defect; it is to pressure-test whether a fallacy attribution is necessary.

## Candidate Policy

Detection uses one candidate per perspective at most. `Non-Fallacious` is a
first-class hypothesis rather than an empty candidate set.

Classification permits the anchor to return a primary and one conditional
alternative. The structural verifier may propose one replacement. The union is
deduplicated and capped at three labels for adjudication. Candidate frequency is
not a vote and does not affect priority.

No agent returns an unconditional top three. This prevents three agents from
covering most of the label space and transferring an underconstrained selection
problem to the judge.

## Disagreement Routing

Debate is skipped when all applicable checks support the anchor and no valid
alternative exists. A debate is triggered by any of these conditions:

- anchor and contextual critic disagree on the detection verdict;
- the structural verifier rejects the anchor's mandatory condition;
- the structural verifier proposes a replacement label;
- classification has more than one valid candidate;
- discourse ownership is disputed;
- the anchor is positive but premise, conclusion, or inferential link is absent.

The router produces a bounded list of claim identifiers. Examples include
`target_owns_claim`, `premise_present`, `sample_to_population`, and
`alternatives_exhaustive`. Debate is limited to at most two conflicts in a fixed
priority order: discourse ownership, inference existence, then subtype
discrimination.

## Targeted Debate

Each debate call receives the raw target, the conflicting claim, and only the
reports relevant to that claim. It returns:

```yaml
claim: string
supporting_position: string
opposing_position: string
decisive_evidence_spans: []
mandatory_test: string
test_result: supports_h1 | supports_h0 | unresolved
resolution_reason: string
```

The debate cannot introduce a new label. An unresolved debate preserves both
hypotheses for the judge.

## Symmetric Judge

For detection, the judge always receives two explicit hypotheses:

- H1: the target commits a named fallacy, with its mandatory condition and
  evidence;
- H0: the target is non-fallacious, with the strongest charitable interpretation
  and the alleged missing condition.

For classification, the judge receives at most three labels, each represented by
its strongest supporting and opposing evidence. The judge must select exactly one
label.

Required output:

```yaml
selected_verdict: Fallacious | Non-Fallacious
selected_candidate: label | null
decisive_claim: string
evidence_spans: []
opposing_case_failure: string
decision_reason: string
```

Detection invariants:

- `Non-Fallacious` requires `selected_candidate=null`;
- `Fallacious` requires a candidate and a satisfied mandatory condition;
- changing a negative anchor to positive requires structural confirmation;
- changing a positive anchor to negative requires a concrete missing condition,
  discourse-ownership failure, or resolved counterevidence;
- unresolved evidence preserves the anchor.

Classification invariants:

- exactly one candidate must be selected;
- the selected label must belong to the bounded candidate union;
- candidate counts and agent agreement are not evidence.

## Contract Verification And Failures

The final verifier is deterministic. It validates schema, allowed labels,
evidence-span provenance, verdict/candidate consistency, and override rules. It
does not call an LLM and cannot change a semantically valid decision.

Malformed provider output follows the existing retry policy. A sample failure is
recorded and the run remains incomplete; failed samples are never silently
dropped from metrics. Resume must preserve completed traces and rerun only missing
samples.

Every trace records the anchor, both perspectives, routed disagreements, debate
resolutions, final hypotheses, judge output, stage transitions, and call/token/time
statistics.

## Verification And Runs

Implementation is verified with the repository's existing automated test suite.
Focused tests cover stage schemas, deterministic routing, override invariants,
trace completeness, resume behavior, and final metric generation.

After tests pass, run the full detection and classification test splits once.
Results use the existing metric format:

- detection: accuracy, positive-class precision, recall, F1, false-positive rate,
  false-negative rate, per-class scores, and confusion matrix;
- classification: accuracy, macro-F1, per-label scores, and confusion matrix;
- both tasks: calls, tokens, and wall time in sample traces and CSV output.

The new run directories preserve the existing manifest, metrics, predictions,
samples, audit, and trace artifacts so results can be compared directly with the
current single-LLM and multi-agent runs.

## Success Criteria

The implementation is complete when:

- both full test runs complete without failed or silently dropped samples;
- detection and classification report the same metrics as the current runners;
- every final decision is traceable to target evidence and an explicit mandatory
  condition;
- no gold label or annotation metadata enters model-visible input.

The resulting metrics are compared directly with the existing single-LLM and
multi-agent baselines. Calls, tokens, and wall time are reported alongside model
quality.
