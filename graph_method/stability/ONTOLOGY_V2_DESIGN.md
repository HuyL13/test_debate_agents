# Ontology revision proposal: separate source, assertions, warrants and conflicts

Status: design motivated by real-source failures and the literature survey; NOT a validated replacement pipeline. Existing revisions and raw outputs remain unchanged.

## Why the current representation is insufficient

An author can reject the sufficiency of a proposed reason without denying the target claim's truth. Conversely, the author can offer additional choices while also rejecting an exhaustive restriction. A single `stance` and `alternatives` tuple attached to an inference whose conclusion is a literal negative sentence conflates these acts. Some disagreements between existing outputs are representational ambiguity, not necessarily semantic errors.

Likewise, a hypothetical action, its forecast consequence and the recommendation justified by the risk are distinct objects. Putting the recommendation at the end of a harm chain is an actual semantic error. Increasing JSON validity cannot resolve these distinctions.

## Proposed core

| Object | Meaning | Required grounding |
|---|---|---|
| SourceSpan | Immutable text and offsets | Exact comment/title/parent substring |
| Proposition | Content being discussed, not automatically asserted true | One or more span anchors; explicit versus reconstructed status |
| Assertion | Who asserts, queries, recommends or reports a proposition | Speaker/source, speech act, qualification and polarity anchors |
| InferenceApplication | Particular offered reasons supporting a target | Premise/target assertions plus source evidence that this link is offered |
| ConflictApplication | Rebuttal of a claim or undercutting of a justification | Rejection assertion and precise target proposition/application |
| PreferenceApplication | Contextual preference between issues/actions | Compared items, direction and stated criterion |
| EventMention | Initial hypothetical action or projected consequence | Source span and scenario/temporal role; does not assert actual occurrence |
| SchemeHypothesis | A neutral scheme proposed for an inference | Role bindings, evidence obligations, verified/ambiguous/rejected status |

Inference, conflict and preference applications follow the representation distinction in [AIF](https://jmvidal.cse.sc.edu/library/chesnevar06a.pdf). The remaining source/provenance and uncertainty details are our extensions, not claims about the complete AIF standard.

## Relations and invariants

- `ANCHORS`: semantic object to immutable span. Normalized content never replaces the source.
- `ASSERTS` / `REPORTS` / `RECOMMENDS` / `QUERIES`: scoped ownership and speech act. A reported assertion is not automatically adopted.
- `PREMISE_OF` / `TARGETS`: reasons and targets of an application. Source fidelity means the author offers the link; it does not mean the reasoning is logically valid.
- `REBUTS`: conflict targets a proposition. `UNDERCUTS`: conflict targets an inference application. Do not encode both as positive support for a negative surface sentence.
- `PREFERS_OVER`: preference direction with its stated criterion. A resource priority is not automatically an exhaustive dilemma.
- `PROJECTED_NEXT`: only scenario event mentions, with initial-action/consequence roles and modal qualification. A recommendation assertion is not automatically an event. A recommended action may also be the hypothetical initial condition of a forecast, with distinct semantic roles.
- `ADOPTS`: a reply adopts a specific parent assertion or application. Store the reply's qualification separately; do not overwrite the parent's wording or inherit all its arguments.

Reconstructed targets, implicit premises and unresolved references must be marked as such. They cannot be presented as literal author assertions. Unsupported content stays unresolved; do not delete every difficult inference merely to improve precision.

## Scheme-specific evidence obligations

Scheme assignment should bind roles, not only emit a category:

| Scheme | Minimal role evidence to inspect |
|---|---|
| testimony | Attributed source contribution and its use as justification; an author's own assertion alone is insufficient |
| consensus | Collective belief, popularity or collective choice functioning as a reason; a statement about people is insufficient |
| historical practice | Tradition/precedent/age offered or explicitly challenged as justification; distinguish description from warrant |
| natural property | Naturalness/normality functioning as evaluative justification; distinguish ordinary physical causation |
| priority comparison | Focal issue, comparison issue, relative criterion and dismissing/deprioritizing act |
| alternatives | Actual choice set and its exhaustiveness, scoped to its proponent; separate author rejection and additional options |
| generalization | Observed case/sample/property, broader target and scope transition; a forecast alone is insufficient |
| causal projection | Initial action/condition, projected outcome, modal strength and any resulting recommendation |

These obligations are an operational adaptation of scheme templates and source verification. They are NOT a proven complete logical characterization of each scheme. Uncertain scheme identity can have multiple hypotheses while preserving one well-grounded relation.

## Concrete regression cases

For 524:10868, the comment criticizes sole reliance on tradition and recommends modern medicine. Its graph should preserve the critique and the positive recommendation separately. It should not invent a closed choice between tradition and medicine. Any reconstructed tradition-based justification being criticized must be marked as an implied target of the rebuttal.

For 35:3103, preserve BOTH the rejected two-option restriction and the author's additional options. `uses open alternatives` and `critiques a restriction` can be compatible descriptions of different acts; a single enum should not force them to compete.

For 469:8603, allowing blocking is a proposed initial condition, blocking critics is a qualified projected outcome, and safeguarding speech is a recommendation. The last item must not be represented as increasing harm in the forecast.

For 229:5485, include the universal coverage claim and the contradictory charging report when representing their conflict. Source distrust is a further inference; it should not be silently substituted for the conflict itself.

## Pattern induction

Merge templates by semantic roles and verified relations, abstracting entities into variables. Preserve alternative witnessed prototypes; do not union incompatible links into an artificial reasoning path. Count distinct articles and retain provenance to every witness. Keep endorsed and criticized scheme occurrences distinct. Match uncertain scheme hypotheses as candidates with explicit status; the final verifier still checks source ownership and defects.

## Validation before adoption

Compare this representation against the current simpler graph on the diagnosed cases and fresh real sources. Measure relation precision, central-link coverage, attribute grounding, reconstruction status and repeated semantic consistency. Added ontology detail is justified only if it improves these measures. No claim of zero errors or stability follows from the design alone.

## Literal anchor implementation (source r3)

The model emits exact source quotes with unit IDs, occurrence numbers, and explicit proposition/application IDs. Code alone resolves whitespace token offsets, checks literal alignment and references, and compiles the canonical graph. Quote matching may normalize whitespace and include enclosing punctuation; it rejects clipped alphanumeric content such as can inside can't. Downstream warrant and candidate verification receive each proposition's actual literal text plus canonical ID/index, avoiding manual token reconstruction. This removes offset-counting errors; it does not establish the semantic truth of application direction or ownership.
