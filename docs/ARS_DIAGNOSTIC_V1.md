# ARS Diagnostic V1

## Motivation

The system uses theory-grounded argument-quality dimensions:

- Acceptability
- Relevance
- Sufficiency

instead of heuristic specialist roles.

## Flow

Input
-> ARSArgumentDecomposer
-> Acceptability / Relevance / Sufficiency
-> optional synchronous role-preserving review
-> ARSArbiter
-> final task label

## Label visibility

| Component | Sees label ontology |
|---|---|
| ARSArgumentDecomposer | No |
| Acceptability | No |
| Relevance | No |
| Sufficiency | No |
| ARS Review | No |
| ARSArbiter | Yes |

## Policies

- `ars_no_debate`
- `ars_review`

## Baselines retained

- `diagnostic_no_debate`
- `diagnostic_review`
- legacy planner/debate
- `single`
