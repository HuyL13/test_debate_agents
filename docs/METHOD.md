# Method

The system implements Unified Multi-Perspective Adjudication for CoCoLoFa.

## Flow

1. `structure` analyzes inferential form and mandatory structural slots.
2. `goal` analyzes the conclusion, justificatory function, and discourse ownership.
3. `counterargument` compares the strongest objection with the strongest defense.
4. Application code builds non-destructive candidate dossiers from all reports.
5. Detection always compares candidate dossiers with an explicit
   `Non-Fallacious` hypothesis in one `comparative_adjudication` call.
6. Classification directly returns a unanimous, uncontested singleton; all other
   cases use one comparative call. Empty candidate sets trigger full-label recovery.

There is no pairwise resolver tournament and no viability-based candidate deletion.
Candidate counts are not votes. Every mandatory condition, reason, and evidence item
remains attached to the report and label that produced it.

## Contracts

Each analyst returns a verdict, at most one candidate, a mandatory condition,
whether that condition is satisfied, a decision reason, an opposing reason, and
TARGET-only evidence IDs. Role-specific fields preserve structure, argument
function, and adversarial objection/defense information.

The final adjudicator returns a verdict, candidate or null, decisive condition,
decision reason, evidence, and explicit failed conditions for rejected candidates.
Detection may reject every candidate; classification must select one label.

## Contrastive Checks

- Hasty Generalization requires a sample-to-population inference.
- Slippery Slope requires an unsupported consequence progression.
- False Dilemma requires alternatives plus an exhaustiveness commitment.
- Appeal to Worse Problems requires dismissal, downplaying, or deprioritization.
- Appeal to Authority requires authority or status to perform justificatory work.

The prompts also preserve modality, negation, quotation, criticism, and the
ownership boundary between TARGET and its context.

## Trace

Per-sample YAML traces contain raw input, three initial reports, candidate dossiers,
the routing decision, final adjudication, prediction, and call/token/time stats.
Terminal output prints each report immediately after its call completes.
