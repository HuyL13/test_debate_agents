# Grounded argument graph ontology, experimental revision 10

The ontology separates the author's argument from the judgment that it is fallacious. A train label is attached to the whole training example and used only for pattern induction. It is never supplied to source extraction or source review.

## Node types

| Type | Meaning | Identity |
|---|---|---|
| proposition | An immutable source span, possibly a conditional fragment | source field, start and end character offsets |
| inference | One application of one reasoning warrant to a conclusion | application ID within the example |
| reasoning_move | Groups different warrant applications supporting the same argumentative move | move ID within the example |

Proposition nodes retain original text, comment/title/parent ownership and, where applicable, the enclosing clause. They are not canonicalized by string similarity. Two mentions of the same person do not automatically denote the same proposition. A title supplies context, not an author conclusion. Parent arguments enter only when the reply adopts the particular link, retaining the reply's qualification.

## Relations

| Relation | Source → destination | Meaning |
|---|---|---|
| PREMISE_OF | proposition → inference | This exact span supplies a reason for this application |
| CONCLUDES | inference → proposition | The application supports or evaluates this conclusion |
| PROJECTED_NEXT | proposition → proposition | Explicit successive projected events; attributed to a particular inference |
| IMPLEMENTS_MOVE | inference → reasoning_move | Applications belong to the same reasoning move |

An inference cannot use its own conclusion as a premise. Multiple applications can share a conclusion but retain their own premise sets. Event order and ordinary adjacency are different relations.

## Inference attributes

`operator`: testimony, consensus, historical_practice, natural_property, priority_comparison, alternatives, generalization, causal_projection, analogy, evidence, other. These are neutral reasoning schemes. A sound argument can instantiate any of them.

`stance`: uses, critiques, reports, unclear. This expresses the current author's relation to the warrant, not the emotional polarity of the conclusion.

`commitment`: certain, probable, possible, normative, unspecified. Prescriptions and confidence are distinguished. Conditional fragments must be read with their source envelope.

`scope_change`: broader, same, narrower, unclear, na. Applicable only to generalization. `alternatives`: closed, open, denied, unclear, na. Applicable only to alternatives. `chain`: ordered source IDs for at least two stated projected events, or empty. `escalation`: increasing_harm, non_escalating, unclear, na. Increasing harm describes a trajectory, not proof that it is unreasonable.

## Train merge and test matching

The current implementation merges witnessed *typed motifs*, not raw text nodes. It mines premise–inference–conclusion templates with an obligatory operator and optional inference constraints. It records mappings to original witnesses and counts support by distinct article, so multiple warrants or comments from one article cannot inflate support. Several prototypes can belong to a label; the union is its pattern graph collection. This is currently a motif collection rather than a single connected graph or a full frequent-subgraph miner.

Patterns are evaluated against competing labels for discrimination and resampled article sets for recovery. Accepted cores require at least five distinct positive articles and at least 80% recovery. Retrieval returns instantiated source-node mappings, actual premise IDs and conclusion IDs, not merely label similarity. The verifier separately checks the mapping, mechanism, author ownership and evidence of a defect. Code calculates scores and selects a candidate while retaining whether the selection is confirmed, weak or forced.

## Known limitations under active experiment

Format constraints guarantee real IDs, not valid reasoning. Revision 10 can overproduce testimony from the author's own assertions, skip intermediate conclusions and inadequately anchor qualified parent risks. Synthetic controls, manual real-source audit, article-disjoint recall and repeatability must all pass before this ontology and extraction procedure are called stable. Test data has not been used for tuning.
