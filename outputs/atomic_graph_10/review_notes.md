# Review notes for the 10-comment smoke test

These are manual review observations, separate from structural validation.
The graphs are model outputs, not gold annotations or corrected graphs.
Model: `openai/gpt-oss-20b`, NVIDIA API, `reasoning_effort=low`.
Selection: test split, seed 42, ten complete comments; no gold labels supplied.

All ten graph files pass the structural validator and match their saved deterministic
linearizations. Totals: 69 propositions, 10 discourse edges, **zero SUPPORT edges**.
This does not establish semantic correctness. The absence of SUPPORT across this
argument-containing selection is a quality concern requiring review.

| Sample | Observed issue |
|---|---|
| `565:8893` | Source question “Who would not find that exciting and a push towards a greater future?” becomes a statement in P05 with mode HEDGED. P03 also reads “only one country” as “the only country mentioned”, shifting meaning. |
| `174:5320` | The text moves from majority belief to enforcing its will, but the graph contains no SUPPORT edge. Review whether the first claim justifies the second under the author's argument. |
| `146:3885` | P02 asserts government involvement while P03 separately adds the original hedge “it appears”; this duplicates content and weakens scope preservation. The source normative “should continue” is labeled ASSERTED. |
| `304:6310` | Conditional antecedent becomes ASSERTED P01. P02 states that others' rights are taken, although the source asks a hypothetical question. This violates preservation of conditional/question scope. |
| `296:10185` | The model splits subject/event and predicate into separate fragments: P01 “Waving off concerns as too simplistic” and P02 “may harm ...”. P04 “never disparaged” also lacks its subject. These are not standalone atomic propositions. |
| `172:9813` | The conditional source “If it takes the courts ...” becomes ASSERTED P07; P08 “So be it” is also ASSERTED. The conditional discourse edge does not restore the missing node scope. |

Structural validation checks schema, IDs, source sentence coverage, connective presence and SUPPORT acyclicity. It cannot prove the interpretation of relations, atomicity or preservation of meaning.

Before downstream classification, add contrastive extraction examples for questions, hedges and conditionals, plus examples distinguishing SUPPORT from discourse. A separate source-grounded semantic review/repair stage could check these errors while keeping the graph ontology closed. Empty SUPPORT arrays should be reviewed on actual arguments, without forcing every node to have an edge.
