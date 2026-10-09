# ARS Architecture — Line-by-Line Refactor Plan

> **Repo:** `https://github.com/HuyL13/test_debate_agents.git`  
> **Target branch:** create a new feature branch from current `main`  
> **Goal:** Add a new **theory-grounded ARS architecture**:
>
> `Argument Decomposer -> Acceptability / Relevance / Sufficiency -> optional role-preserving review -> ARS Arbiter -> final label`
>
> without destroying the existing legacy and Diagnostic Debate V1 baselines.

---

# 0. What must stay unchanged

The current repo already has several experimental paths. Do **not** overwrite them.

Keep all of these unchanged:

```text
single
no_deliberation
fixed
adaptive_policy=planner
adaptive_policy=disagreement
adaptive_policy=diagnostic_no_debate
adaptive_policy=diagnostic_review
flow=A
flow=B
```

The new architecture must be added as:

```text
adaptive_policy=ars_no_debate
adaptive_policy=ars_review
```

This gives a clean ablation later:

```text
single
vs
diagnostic_no_debate
vs
diagnostic_review
vs
ars_no_debate
vs
ars_review
```

---

# 1. Final target architecture

```text
RAW INPUT
    |
    v
ARSArgumentDecomposer
    |
    v
Structured Argument
    |
    +--------------------+--------------------+
    |                    |                    |
    v                    v                    v
Acceptability         Relevance           Sufficiency
Agent                 Agent               Agent
    |                    |                    |
    +--------------------+--------------------+
                         |
                         v
               Independent Diagnoses
                         |
                  optional review
                         |
                         v
                  Final Diagnoses
                         |
                         v
                     ARSArbiter
                         |
                         v
              Detection / Classification
```

## Hard invariant

```text
ARSArgumentDecomposer:
    MUST NOT know task labels.

Acceptability:
    MUST NOT know task labels.

Relevance:
    MUST NOT know task labels.

Sufficiency:
    MUST NOT know task labels.

ARS review:
    MUST NOT know task labels.

ARSArbiter:
    ONLY component allowed to know:
        Fallacious
        Non-Fallacious
        the 8 CoCoLoFa labels
```

---

# 2. Create a feature branch

Run:

```bash
git checkout main
git pull
git checkout -b feat/ars-diagnostic
```

Do not develop this directly on `main`.

---

# 3. File map

## Create

```text
src/ars_prompts.py
src/ars_schemas.py
src/ars_diagnostic.py

tests/test_ars_diagnostic.py

configs/detection.ars_no_debate.yaml
configs/detection.ars.yaml
configs/classification.ars_no_debate.yaml
configs/classification.ars.yaml

docs/ARS_DIAGNOSTIC_V1.md
```

## Modify

```text
src/labels.py
src/engine.py
README.md
```

## Do NOT modify in V1

```text
src/diagnostic.py
src/prompts.py
src/schemas.py
src/simplified.py
src/evaluate.py
src/runner.py
src/legacy_protocols/*
```

Reason:

- `src/diagnostic.py` is your current baseline.
- `src/prompts.py` is used by legacy / old diagnostic code.
- `src/schemas.py` is already shared by old code.
- isolating ARS prevents accidental regression.

---

# 4. Modify `src/labels.py`

Current important section:

```python
FALLACIES = (
    'Appeal to Authority', 'Appeal to Majority', 'Appeal to Nature',
    'Appeal to Tradition', 'Appeal to Worse Problems', 'False Dilemma',
    'Hasty Generalization', 'Slippery Slope',
)

DETECTION = ('Non-Fallacious', 'Fallacious')

ROLES = ('Factual', 'Logical', 'Contextual')

DIAGNOSTIC_ROLES = ('Inference', 'Evidence', 'SemanticContext')

PROTOCOLS = ('round_robin', 'point_counterpoint', 'cross_examination')
```

## Add these lines immediately after `DIAGNOSTIC_ROLES`

```python
ARS_ROLES = ('Acceptability', 'Relevance', 'Sufficiency')

ARS_SPECIAL_ROLES = ('ARSArgumentDecomposer', 'ARSArbiter')
```

Final section should look like:

```python
ROLES = ('Factual', 'Logical', 'Contextual')

DIAGNOSTIC_ROLES = ('Inference', 'Evidence', 'SemanticContext')

ARS_ROLES = ('Acceptability', 'Relevance', 'Sufficiency')

ARS_SPECIAL_ROLES = ('ARSArgumentDecomposer', 'ARSArbiter')

PROTOCOLS = ('round_robin', 'point_counterpoint', 'cross_examination')
```

Do **not** rename:

```python
DIAGNOSTIC_ROLES
```

because old diagnostic experiments depend on it.

---

# 5. Create `src/ars_schemas.py`

Create a completely new file:

```python
from src.labels import DETECTION, FALLACIES
from src.schemas import object_schema, validate_output


DIMENSION_STATUS = (
    'satisfied',
    'violated',
    'uncertain',
    'not_applicable',
)
```

---

## 5.1 Add decomposition check schema

Paste below:

```python
def decomposition_check_schema():
    return object_schema({
        'status': {
            'type': 'string',
            'enum': [
                'accept',
                'partially_correct',
                'incorrect',
            ],
        },
        'corrections': {
            'type': 'array',
            'maxItems': 3,
            'items': {
                'type': 'string',
                'maxLength': 220,
            },
        },
    })
```

Purpose:

Every specialist can say:

```json
{
  "status": "partially_correct",
  "corrections": [
    "C2 preserves the qualifier 'might'."
  ]
}
```

This prevents:

```text
Decomposer wrong
-> all specialists blindly inherit same error
```

---

# 6. Add ARS Argument Decomposer schema

Still inside:

```text
src/ars_schemas.py
```

Add:

```python
def ars_argument_schema():
    claim_schema = object_schema({
        'id': {
            'type': 'string',
            'minLength': 1,
            'maxLength': 24,
        },

        'source': {
            'type': 'string',
            'enum': [
                'title',
                'article',
                'parent_comment',
                'target_comment',
            ],
        },

        'role': {
            'type': 'string',
            'enum': [
                'premise',
                'conclusion',
                'intermediate_conclusion',
                'evidence',
                'background',
                'stance',
                'other',
            ],
        },

        'text': {
            'type': 'string',
            'minLength': 1,
            'maxLength': 300,
        },

        'qualifiers': {
            'type': 'array',
            'maxItems': 4,
            'items': {
                'type': 'string',
                'maxLength': 60,
            },
        },

        'modality': {
            'type': 'string',
            'enum': [
                'asserted',
                'tentative',
                'conditional',
                'normative',
                'question',
                'other',
            ],
        },
    })

    assumption_schema = object_schema({
        'id': {
            'type': 'string',
            'minLength': 1,
            'maxLength': 24,
        },

        'text': {
            'type': 'string',
            'minLength': 1,
            'maxLength': 260,
        },

        'basis': {
            'type': 'string',
            'enum': [
                'linguistic',
                'contextual',
                'speaker_commitment',
                'scheme_based',
                'unclear',
            ],
        },

        'certainty': {
            'type': 'string',
            'enum': [
                'high',
                'medium',
                'low',
            ],
        },
    })

    inference_link_schema = object_schema({
        'from': {
            'type': 'array',
            'minItems': 1,
            'maxItems': 5,
            'items': {
                'type': 'string',
                'maxLength': 24,
            },
        },

        'to': {
            'type': ['string', 'null'],
            'maxLength': 24,
        },

        'relation': {
            'type': 'string',
            'enum': [
                'support',
                'attack',
                'causal',
                'generalization',
                'normative_support',
                'alternative_structure',
                'other',
            ],
        },
    })

    return object_schema({
        'argumentative_status': {
            'type': 'string',
            'enum': [
                'explicit_argument',
                'implicit_argument',
                'assertion',
                'question',
                'sarcasm',
                'fragment',
                'unclear',
            ],
        },

        'claims': {
            'type': 'array',
            'maxItems': 8,
            'items': claim_schema,
        },

        'main_conclusion_id': {
            'type': ['string', 'null'],
            'maxLength': 24,
        },

        'implicit_assumptions': {
            'type': 'array',
            'maxItems': 4,
            'items': assumption_schema,
        },

        'inference_links': {
            'type': 'array',
            'maxItems': 5,
            'items': inference_link_schema,
        },

        'scope_notes': {
            'type': 'array',
            'maxItems': 4,
            'items': {
                'type': 'string',
                'maxLength': 220,
            },
        },

        'uncertainty': {
            'type': 'array',
            'maxItems': 4,
            'items': {
                'type': 'string',
                'maxLength': 220,
            },
        },
    })
```

---

# 7. Why this Decomposer schema is different

Your old structure mainly had:

```text
claim
source
role
text
```

The new version explicitly preserves:

```text
qualifiers
modality
implicit assumptions
inference links
provenance
scope
uncertainty
```

This is important for errors like:

```text
"might"
becoming
"definitely"
```

or:

```text
"some"
becoming
"all"
```

---

# 8. Add Acceptability schema

In `src/ars_schemas.py`, add:

```python
def acceptability_schema():
    return object_schema({
        'decomposition_check': decomposition_check_schema(),

        'premise_ids': {
            'type': 'array',
            'maxItems': 5,
            'items': {
                'type': 'string',
                'maxLength': 24,
            },
        },

        'dimension_status': {
            'type': 'string',
            'enum': list(DIMENSION_STATUS),
        },

        'acceptability_basis': {
            'type': 'string',
            'enum': [
                'textual',
                'contextual',
                'speaker_commitment',
                'none',
            ],
        },

        'problematic_commitment': {
            'type': 'string',
            'maxLength': 260,
        },

        'finding': {
            'type': 'string',
            'minLength': 1,
            'maxLength': 360,
        },

        'supporting_quote': {
            'type': 'string',
            'minLength': 1,
            'maxLength': 220,
        },

        'charitable_reading': {
            'type': 'string',
            'maxLength': 300,
        },
    })
```

Interpretation:

```text
satisfied
= premise can be provisionally accepted

violated
= target/context itself undermines the premise

uncertain
= supplied context conflicts or is ambiguous

not_applicable
= requires outside factual verification
```

Important:

```text
No external fact checking
!=
premise false
```

Therefore:

```text
cannot verify
-> not_applicable
```

not:

```text
cannot verify
-> violated
```

---

# 9. Add Relevance schema

Add:

```python
def relevance_schema():
    return object_schema({
        'decomposition_check': decomposition_check_schema(),

        'premise_ids': {
            'type': 'array',
            'maxItems': 5,
            'items': {
                'type': 'string',
                'maxLength': 24,
            },
        },

        'conclusion_id': {
            'type': ['string', 'null'],
            'maxLength': 24,
        },

        'dimension_status': {
            'type': 'string',
            'enum': list(DIMENSION_STATUS),
        },

        'relevance_gap': {
            'type': 'string',
            'maxLength': 300,
        },

        'finding': {
            'type': 'string',
            'minLength': 1,
            'maxLength': 360,
        },

        'supporting_quote': {
            'type': 'string',
            'minLength': 1,
            'maxLength': 220,
        },

        'charitable_reading': {
            'type': 'string',
            'maxLength': 300,
        },
    })
```

This agent answers only:

```text
Assume premise is acceptable.

Does it actually count as a reason
for accepting the conclusion?
```

---

# 10. Add Sufficiency schema

Add:

```python
def sufficiency_schema():
    return object_schema({
        'decomposition_check': decomposition_check_schema(),

        'premise_ids': {
            'type': 'array',
            'maxItems': 5,
            'items': {
                'type': 'string',
                'maxLength': 24,
            },
        },

        'conclusion_id': {
            'type': ['string', 'null'],
            'maxLength': 24,
        },

        'dimension_status': {
            'type': 'string',
            'enum': list(DIMENSION_STATUS),
        },

        'missing_warrant': {
            'type': 'string',
            'maxLength': 300,
        },

        'scope_or_strength_gap': {
            'type': 'string',
            'maxLength': 300,
        },

        'finding': {
            'type': 'string',
            'minLength': 1,
            'maxLength': 360,
        },

        'supporting_quote': {
            'type': 'string',
            'minLength': 1,
            'maxLength': 220,
        },

        'charitable_reading': {
            'type': 'string',
            'maxLength': 300,
        },
    })
```

Sufficiency asks:

```text
Assume premise is acceptable.

Assume premise is relevant.

Is the support strong enough
for a conclusion of this scope/strength?
```

---

# 11. Add ARS schema dispatcher

Add:

```python
def ars_diagnosis_schema(role):
    mapping = {
        'Acceptability': acceptability_schema,
        'Relevance': relevance_schema,
        'Sufficiency': sufficiency_schema,
    }

    if role not in mapping:
        raise ValueError(f'Unknown ARS role: {role}')

    return mapping[role]()
```

---

# 12. Add review schema

Add:

```python
def ars_review_schema(role):
    diagnosis = ars_diagnosis_schema(role)

    return object_schema({
        'review_action': {
            'type': 'string',
            'enum': [
                'keep',
                'revise',
                'withdraw',
            ],
        },

        'peer_effect': {
            'type': 'string',
            'maxLength': 320,
        },

        **diagnosis['properties'],
    })
```

Meaning:

```text
keep
= initial diagnosis still stands

revise
= another dimension exposed a real weakness

withdraw
= initial claimed violation is no longer defensible
```

---

# 13. Add Arbiter schema

Add:

```python
def ars_arbiter_schema(task):
    validated_dimensions = object_schema({
        'acceptability': {
            'type': 'string',
            'enum': [
                'supported',
                'unsupported',
                'uncertain',
                'not_applicable',
            ],
        },

        'relevance': {
            'type': 'string',
            'enum': [
                'supported',
                'unsupported',
                'uncertain',
                'not_applicable',
            ],
        },

        'sufficiency': {
            'type': 'string',
            'enum': [
                'supported',
                'unsupported',
                'uncertain',
                'not_applicable',
            ],
        },
    })

    if task == 'detection':
        return object_schema({
            'validated_dimensions': validated_dimensions,

            'candidate_type': {
                'type': 'string',
                'enum': [
                    *FALLACIES,
                    'None',
                ],
            },

            'nearest_competitor': {
                'type': 'string',
                'enum': [
                    *FALLACIES,
                    'None',
                ],
            },

            'mapping_reason': {
                'type': 'string',
                'minLength': 1,
                'maxLength': 500,
            },

            'prediction': {
                'type': 'string',
                'enum': list(DETECTION),
            },

            'content': {
                'type': 'string',
                'minLength': 1,
                'maxLength': 500,
            },
        })

    if task == 'classification':
        return object_schema({
            'validated_dimensions': validated_dimensions,

            'candidate_type': {
                'type': 'string',
                'enum': list(FALLACIES),
            },

            'nearest_competitor': {
                'type': 'string',
                'enum': list(FALLACIES),
            },

            'mapping_reason': {
                'type': 'string',
                'minLength': 1,
                'maxLength': 500,
            },

            'prediction': {
                'type': 'string',
                'enum': list(FALLACIES),
            },

            'content': {
                'type': 'string',
                'minLength': 1,
                'maxLength': 500,
            },
        })

    raise ValueError(f'Unknown task: {task}')
```

---

# 14. Add Arbiter semantic validator

Still in `src/ars_schemas.py`:

```python
def validate_ars_arbiter(value, task):
    validate_output(
        value,
        ars_arbiter_schema(task),
    )

    if task == 'detection':
        candidate = value['candidate_type']
        prediction = value['prediction']

        if candidate == 'None':
            if prediction != 'Non-Fallacious':
                raise ValueError(
                    'candidate_type=None requires Non-Fallacious'
                )

        else:
            if prediction != 'Fallacious':
                raise ValueError(
                    'A supported closed-set candidate requires Fallacious'
                )

        return

    if task == 'classification':
        if value['candidate_type'] != value['prediction']:
            raise ValueError(
                'classification candidate_type must equal prediction'
            )

        return

    raise ValueError(f'Unknown task: {task}')
```

---

# 15. Add Decomposer structural validator

Add:

```python
def validate_ars_decomposition(value, input_dict):
    validate_output(
        value,
        ars_argument_schema(),
    )

    claims = value['claims']

    claim_ids = [
        claim['id']
        for claim in claims
    ]

    if len(claim_ids) != len(set(claim_ids)):
        raise ValueError(
            'Claim IDs must be unique'
        )

    claims_by_id = {
        claim['id']: claim
        for claim in claims
    }

    assumption_ids = {
        assumption['id']
        for assumption in value['implicit_assumptions']
    }

    all_ids = (
        set(claims_by_id)
        | assumption_ids
    )

    main_conclusion_id = value['main_conclusion_id']

    if (
        main_conclusion_id is not None
        and main_conclusion_id not in claims_by_id
    ):
        raise ValueError(
            'main_conclusion_id must reference a claim'
        )

    for link in value['inference_links']:
        for source_id in link['from']:
            if source_id not in all_ids:
                raise ValueError(
                    f'Unknown inference source: {source_id}'
                )

        target_id = link['to']

        if (
            target_id is not None
            and target_id not in all_ids
        ):
            raise ValueError(
                f'Unknown inference target: {target_id}'
            )

    source_text = {
        'title':
            input_dict.get('title', ''),

        'article':
            input_dict.get('article', '') or '',

        'parent_comment':
            input_dict.get('parent_comment', ''),

        'target_comment':
            input_dict.get('comment', ''),
    }

    for claim in claims:
        declared_source = claim['source']
        claim_text = claim['text']

        if claim_text not in source_text[declared_source]:
            raise ValueError(
                f"Claim {claim['id']} must be verbatim "
                f"in declared source {declared_source}"
            )
```

Purpose:

The LLM may not write:

```text
"the author claims everyone supports X"
```

unless that exact text actually appears in the declared source.

---

# 16. Add label-leakage validator

Still in `src/ars_schemas.py`.

Add:

```python
FORBIDDEN_GENERATED_TERMS = tuple(
    term.casefold()
    for term in (
        *FALLACIES,
        'Fallacious',
        'Non-Fallacious',
        'fallacy',
        'fallacious',
    )
)
```

Then:

```python
def _generated_strings(value):
    if isinstance(value, dict):
        for key, subvalue in value.items():

            if key in {
                'text',
                'supporting_quote',
            }:
                continue

            yield from _generated_strings(
                subvalue
            )

    elif isinstance(value, list):
        for item in value:
            yield from _generated_strings(item)

    elif isinstance(value, str):
        yield value
```

Then:

```python
def validate_label_agnostic(value):
    generated_text = ' '.join(
        _generated_strings(value)
    ).casefold()

    for term in FORBIDDEN_GENERATED_TERMS:
        if term in generated_text:
            raise ValueError(
                'Label-aware language is forbidden '
                f'before arbitration: {term}'
            )
```

Important:

Do **not** inspect:

```text
supporting_quote
claim.text
```

because the original user text may literally contain:

```text
"slippery slope"
```

That is not model leakage.

---

# 17. Add quote validation

Add:

```python
def _normalize_text(text):
    return ' '.join(
        text.split()
    ).casefold()
```

Then:

```python
def validate_target_quote(
    value,
    target_comment,
):
    quote = _normalize_text(
        value['supporting_quote']
    )

    target = _normalize_text(
        target_comment
    )

    if not quote:
        raise ValueError(
            'supporting_quote must not be empty'
        )

    if quote not in target:
        raise ValueError(
            'supporting_quote must occur '
            'verbatim in target comment'
        )
```

---

# 18. Add specialist validators

Add:

```python
def validate_ars_diagnosis(
    value,
    role,
    target_comment,
):
    validate_output(
        value,
        ars_diagnosis_schema(role),
    )

    validate_label_agnostic(value)

    validate_target_quote(
        value,
        target_comment,
    )
```

Add:

```python
def validate_ars_review(
    value,
    role,
    target_comment,
):
    validate_output(
        value,
        ars_review_schema(role),
    )

    validate_label_agnostic(value)

    validate_target_quote(
        value,
        target_comment,
    )
```

---

# 19. Create `src/ars_prompts.py`

Create a completely separate file.

Do not reuse the current `system_prompt()` for ARS specialist calls.

Paste:

```python
from src.labels import labels_for


ARS_COMMON = (
    'Use only the supplied TITLE, ARTICLE when present, '
    'IMMEDIATE PARENT COMMENT, and TARGET COMMENT. '

    'Judge only reasoning attributable to TARGET. '

    'Do not use external facts or memory to fact-check the world. '

    'Treat the decomposition as a fallible hypothesis. '
    'Verify it against the raw input before accepting it. '

    'Preserve modality, quantifiers, negation, scope, timing, '
    'conditionality and uncertainty. '

    'Do not output a task label. '
    'Do not name a logical-fallacy class. '

    'Missing citations, strong opinions, advocacy, predictions, '
    'normative language or unavailable external evidence do not '
    'automatically establish a reasoning defect. '

    'Return only JSON matching the provided schema. '
)
```

---

# 20. Add Decomposer prompt

Continue in `src/ars_prompts.py`:

```python
DECOMPOSER_PROMPT = (
    'You are an argument-structure decomposer. '

    'Your only task is to represent the structure of the supplied argument. '

    'Extract claims verbatim and preserve their source provenance. '

    'Preserve qualifiers such as may, might, could, should, probably, '
    'sometimes, usually, some, many, all and conditionals. '

    'Distinguish premise, conclusion, intermediate conclusion, '
    'evidence, background, stance and other material. '

    'Reconstruct only minimal implicit assumptions licensed by '
    'linguistic form, context, speaker commitment or argument structure. '

    'Do not invent assumptions merely to make the argument complete. '

    'If structure is uncertain, record uncertainty. '

    'Build explicit inference links between claims and assumptions. '

    'Do not evaluate whether the argument is good or bad. '
)
```

---

# 21. Add Acceptability prompt

```python
ACCEPTABILITY_PROMPT = (
    'You are the Acceptability specialist. '

    'Evaluate ACCEPTABILITY only. '

    'Ask whether the premises or commitments can be provisionally '
    'accepted based on the supplied text and context. '

    'Do not fact-check external reality. '

    'If acceptability depends on unavailable outside knowledge, '
    'use dimension_status=not_applicable. '

    'Distinguish lack of external verification from contradiction '
    'or weakness visible in the supplied text itself. '

    'Do not evaluate whether a premise is relevant to the conclusion. '

    'Do not evaluate whether the total support is sufficient. '

    'Do not classify the argument. '
)
```

---

# 22. Add Relevance prompt

```python
RELEVANCE_PROMPT = (
    'You are the Relevance specialist. '

    'Evaluate RELEVANCE only. '

    'Assume the identified premise is provisionally acceptable. '

    'Ask whether that premise actually counts as a reason bearing '
    'on the conclusion. '

    'Identify a relevance gap only when the stated reason fails '
    'to materially support the target conclusion. '

    'Do not decide whether the premise is true. '

    'Do not decide whether the total amount of support is sufficient. '

    'Do not classify the argument. '
)
```

---

# 23. Add Sufficiency prompt

```python
SUFFICIENCY_PROMPT = (
    'You are the Sufficiency specialist. '

    'Evaluate SUFFICIENCY only. '

    'Assume the identified premises are provisionally acceptable '
    'and relevant. '

    'Ask whether their combined support is enough for a conclusion '
    'of this strength and scope. '

    'Inspect missing warrants, scope jumps, case-to-group moves, '
    'unsupported consequence chains and claims that alternatives '
    'are exhaustive. '

    'Describe the structural gap without naming a task class. '

    'Do not classify the argument. '
)
```

---

# 24. Add CoCoLoFa ontology only for Arbiter

Still in `src/ars_prompts.py`:

```python
COCOLOFA_RULES = (
    'Appeal to Authority: treating an inappropriate authority '
    'as sufficient proof. '

    'Appeal to Majority: treating popularity as proof of truth '
    'or correctness. '

    'Appeal to Nature: treating naturalness alone as proof of '
    'goodness or correctness. '

    'Appeal to Tradition: treating longstanding practice alone '
    'as justification. '

    'Appeal to Worse Problems: dismissing an issue solely because '
    'worse problems exist. '

    'False Dilemma: improperly restricting available alternatives. '

    'Hasty Generalization: drawing a broad conclusion from '
    'insufficient or unrepresentative cases. '

    'Slippery Slope: asserting an inadequately supported progression '
    'of consequences. '
)
```

---

# 25. Add final `ars_system_prompt()`

```python
ROLE_PROMPTS = {
    'ARSArgumentDecomposer':
        DECOMPOSER_PROMPT,

    'Acceptability':
        ACCEPTABILITY_PROMPT,

    'Relevance':
        RELEVANCE_PROMPT,

    'Sufficiency':
        SUFFICIENCY_PROMPT,
}
```

Then:

```python
def ars_system_prompt(role, task):
    if role in ROLE_PROMPTS:
        return (
            ARS_COMMON
            + ROLE_PROMPTS[role]
        )

    if role != 'ARSArbiter':
        raise ValueError(
            f'Unknown ARS role: {role}'
        )

    if task == 'detection':
        task_instruction = (
            'You are the only label-aware component. '

            'Determine whether TARGET instantiates one of the '
            'eight closed-set CoCoLoFa classes. '

            'If no class is established, output Non-Fallacious. '
        )

    elif task == 'classification':
        task_instruction = (
            'You are the only label-aware component. '

            'TARGET is known to contain one of the eight '
            'closed-set CoCoLoFa classes. '

            'Choose exactly one class. '
        )

    else:
        raise ValueError(
            f'Unknown task: {task}'
        )

    return (
        'Use only the supplied raw text, decomposition and '
        'FINAL ARS diagnoses. '

        'Specialist reports are hypotheses, not votes or facts. '

        'Re-check every decisive specialist claim against TARGET. '

        'Do not reward verbosity, confidence or repeated claims. '

        + task_instruction

        + COCOLOFA_RULES

        + 'Allowed final task labels: '
        + ', '.join(labels_for(task))
        + '. '

        'Map ARS diagnoses to the benchmark ontology only after '
        'validating argument structure. '

        'Identify the nearest competing class and explain why '
        'the decisive structure fits one better than the other. '

        'Return only JSON matching the provided schema. '
    )
```

---

# 26. Create `src/ars_diagnostic.py`

Start with imports:

```python
from copy import deepcopy

from src.ars_schemas import (
    ars_argument_schema,
    ars_diagnosis_schema,
    ars_review_schema,
    validate_ars_decomposition,
    validate_ars_diagnosis,
    validate_ars_review,
)

from src.labels import ARS_ROLES
```

---

# 27. Add `execute()`

Paste:

```python
def execute(
    ask,
    model_input,
    policy,
):
    decomposition = ask(
        'ARSArgumentDecomposer',
        'ars_decomposition',
        {},
        [],
        (
            'Extract a label-agnostic structured '
            'argument representation.'
        ),
        schema=ars_argument_schema(),
        validator=lambda value:
            validate_ars_decomposition(
                value,
                model_input.as_dict(),
            ),
    )

    initial = {}

    for role in ARS_ROLES:
        initial[role] = ask(
            role,
            'ars_initial',
            {},
            [],
            (
                f'Provide an independent '
                f'{role} diagnosis only.'
            ),
            schema=ars_diagnosis_schema(role),
            validator=lambda value, role=role:
                validate_ars_diagnosis(
                    value,
                    role,
                    model_input.comment,
                ),
            extra={
                'decomposition':
                    decomposition,
            },
        )

    final = deepcopy(initial)

    reviews = []

    reason = 'ars_no_debate'
```

---

# 28. Add review branch

Continue in same function:

```python
    if policy == 'ars_review':
        frozen_initial = deepcopy(initial)

        for role in ARS_ROLES:
            output = ask(
                role,
                'ars_review',
                frozen_initial,
                [],
                (
                    'Review your own ARS dimension using the '
                    'immutable initial diagnoses. '

                    'Other dimensions may expose a weakness in '
                    'your analysis, but remain inside your own '
                    'assigned dimension. '

                    'Return keep, revise or withdraw. '

                    'Do not classify the target.'
                ),
                schema=ars_review_schema(role),
                validator=lambda value, role=role:
                    validate_ars_review(
                        value,
                        role,
                        model_input.comment,
                    ),
                extra={
                    'decomposition':
                        decomposition,
                },
            )

            final[role] = output

            reviews.append({
                'round': 0,
                'role': role,
                'kind': 'ars_review',
                **output,
            })

        reason = 'ars_review'
```

Finish:

```python
    return (
        decomposition,
        initial,
        reviews,
        final,
        reason,
    )
```

---

# 29. Why this review is synchronous

Every reviewer gets:

```python
reports=frozen_initial
history=[]
```

So the actual logical structure is:

```text
A0
R0
S0

A1 = review(A0,R0,S0)
R1 = review(A0,R0,S0)
S1 = review(A0,R0,S0)
```

Not:

```text
A1
-> R1 sees A1
-> S1 sees A1 and R1
```

This avoids order effects and conformity cascades.

---

# 30. Modify `src/engine.py`

Current imports include something like:

```python
from src.diagnostic import execute as execute_diagnostic
```

Add immediately below:

```python
from src.ars_diagnostic import execute as execute_ars
```

Add:

```python
from src.ars_prompts import ars_system_prompt
```

Add:

```python
from src.ars_schemas import (
    ars_arbiter_schema,
    validate_ars_arbiter,
)
```

---

# 31. Modify policy allowlist

Find:

```python
if adaptive_policy not in (
    'planner',
    'disagreement',
    'diagnostic_no_debate',
    'diagnostic_review',
):
    raise ValueError('Unknown adaptive policy')
```

Replace with:

```python
if adaptive_policy not in (
    'planner',
    'disagreement',
    'diagnostic_no_debate',
    'diagnostic_review',
    'ars_no_debate',
    'ars_review',
):
    raise ValueError('Unknown adaptive policy')
```

Do not change anything else in constructor.

---

# 32. Modify nested `ask()` inside `Engine.run()`

Currently the code selects system prompt using:

```python
system_prompt=(
    simplified.prompt(role, self.task)
    if self.flow
    else system_prompt(role, self.task)
)
```

Do not leave it like this because ARS roles must use a separate prompt family.

Before `return self.llm.generate(...)`, insert:

```python
            ars_role = role in (
                'ARSArgumentDecomposer',
                'Acceptability',
                'Relevance',
                'Sufficiency',
                'ARSArbiter',
            )
```

Then:

```python
            if ars_role:
                selected_system_prompt = (
                    ars_system_prompt(
                        role,
                        self.task,
                    )
                )

            elif self.flow:
                selected_system_prompt = (
                    simplified.prompt(
                        role,
                        self.task,
                    )
                )

            else:
                selected_system_prompt = (
                    system_prompt(
                        role,
                        self.task,
                    )
                )
```

Then change:

```python
system_prompt=...
```

inside `self.llm.generate()` to:

```python
system_prompt=selected_system_prompt
```

Final relevant section should look conceptually like:

```python
        def ask(...):
            payload = {
                ...
            }

            if decomposition is not None:
                payload['decomposition'] = deepcopy(decomposition)

            ars_role = role in (
                'ARSArgumentDecomposer',
                'Acceptability',
                'Relevance',
                'Sufficiency',
                'ARSArbiter',
            )

            if ars_role:
                selected_system_prompt = (
                    ars_system_prompt(
                        role,
                        self.task,
                    )
                )

            elif self.flow:
                selected_system_prompt = (
                    simplified.prompt(
                        role,
                        self.task,
                    )
                )

            else:
                selected_system_prompt = (
                    system_prompt(
                        role,
                        self.task,
                    )
                )

            return self.llm.generate(
                system_prompt=selected_system_prompt,
                user_prompt=canonical(payload),
                ...
            )
```

---

# 33. Add ARS branch in `Engine.run()`

Locate this existing branch:

```python
if (
    self.mode == 'adaptive'
    and self.adaptive_policy in (
        'diagnostic_no_debate',
        'diagnostic_review',
    )
):
```

Insert the entire ARS branch **immediately before it**.

Paste:

```python
        if (
            self.mode == 'adaptive'
            and self.adaptive_policy in (
                'ars_no_debate',
                'ars_review',
            )
        ):
            selected_protocol = (
                self.adaptive_policy
            )

            (
                decomposition,
                initial,
                history,
                final_agents,
                reason,
            ) = execute_ars(
                ask,
                model_input,
                self.adaptive_policy,
            )

            arbiter = ask(
                'ARSArbiter',
                'ars_final',
                {
                    'final_diagnoses':
                        final_agents,
                },
                [],
                (
                    'Validate the final ARS diagnoses '
                    'against the raw target and map them '
                    'to exactly one final task prediction.'
                ),
                schema=ars_arbiter_schema(
                    self.task
                ),
                validator=lambda value:
                    validate_ars_arbiter(
                        value,
                        self.task,
                    ),
                extra={
                    'decomposition':
                        decomposition,
                },
            )

            return {
                'framework':
                    'ARS',

                'prediction':
                    arbiter['prediction'],

                'planner_protocol':
                    selected_protocol,

                'plan':
                    None,

                'decomposition':
                    decomposition,

                'initial_diagnoses':
                    initial,

                'diagnostic_review':
                    history,

                'final_diagnoses':
                    final_agents,

                'initial_agents':
                    {},

                'deliberation':
                    history,

                'final_agents':
                    {},

                'arbiter':
                    arbiter,

                'stop_reason':
                    reason,

                'latency_seconds':
                    time.monotonic() - started,
            }
```

---

# 34. Important: Arbiter input intentionally excludes history

Notice:

```python
reports={
    'final_diagnoses': final_agents
}

history=[]
```

This is intentional.

Do not pass:

```text
initial diagnoses
+
reviews
+
final diagnoses
```

all at once.

Otherwise the same bad idea may appear multiple times and become more persuasive merely through repetition.

You still keep:

```text
initial_diagnoses
diagnostic_review
final_diagnoses
```

in the saved trace.

You just do not feed all three into the final model call.

---

# 35. Create `tests/test_ars_diagnostic.py`

Start:

```python
import json

import pytest

from src.data.loader import ModelInput
from src.engine import Engine
from src.labels import ARS_ROLES
from src.schemas import validate_output
```

Add:

```python
TARGET = (
    'Many people believe X, '
    'therefore X is true.'
)
```

---

# 36. Add mock LLM

Paste a scripted test model.

```python
class ARSTestLLM:
    def __init__(self):
        self.calls = []

    def generate(
        self,
        *,
        system_prompt,
        user_prompt,
        schema,
        metadata,
        validator=None,
    ):
        payload = json.loads(
            user_prompt
        )

        self.calls.append({
            'metadata':
                metadata.copy(),

            'payload':
                payload,

            'system_prompt':
                system_prompt,

            'schema':
                schema,
        })

        role = metadata['role']

        if role == 'ARSArgumentDecomposer':
            value = {
                'argumentative_status':
                    'explicit_argument',

                'claims': [
                    {
                        'id': 'C1',
                        'source': 'target_comment',
                        'role': 'premise',
                        'text': 'Many people believe X',
                        'qualifiers': [],
                        'modality': 'asserted',
                    },
                    {
                        'id': 'C2',
                        'source': 'target_comment',
                        'role': 'conclusion',
                        'text': 'X is true',
                        'qualifiers': [],
                        'modality': 'asserted',
                    },
                ],

                'main_conclusion_id':
                    'C2',

                'implicit_assumptions':
                    [],

                'inference_links': [
                    {
                        'from': ['C1'],
                        'to': 'C2',
                        'relation': 'support',
                    }
                ],

                'scope_notes':
                    [],

                'uncertainty':
                    [],
            }

        elif role == 'Acceptability':
            value = {
                'decomposition_check': {
                    'status': 'accept',
                    'corrections': [],
                },

                'premise_ids':
                    ['C1'],

                'dimension_status':
                    'satisfied',

                'acceptability_basis':
                    'speaker_commitment',

                'problematic_commitment':
                    '',

                'finding':
                    'The popularity premise is explicitly asserted.',

                'supporting_quote':
                    'Many people believe X',

                'charitable_reading':
                    'Provisionally accept the popularity statement.',
            }

        elif role == 'Relevance':
            value = {
                'decomposition_check': {
                    'status': 'accept',
                    'corrections': [],
                },

                'premise_ids':
                    ['C1'],

                'conclusion_id':
                    'C2',

                'dimension_status':
                    'violated',

                'relevance_gap':
                    'Popularity does not itself bear on truth.',

                'finding':
                    'The stated reason does not directly support truth.',

                'supporting_quote':
                    'Many people believe X',

                'charitable_reading':
                    'Popularity may show common acceptance.',
            }

        elif role == 'Sufficiency':
            value = {
                'decomposition_check': {
                    'status': 'accept',
                    'corrections': [],
                },

                'premise_ids':
                    ['C1'],

                'conclusion_id':
                    'C2',

                'dimension_status':
                    'violated',

                'missing_warrant':
                    'If many people believe a claim, the claim is true.',

                'scope_or_strength_gap':
                    'Prevalence of belief is weaker than truth.',

                'finding':
                    'The premise is insufficient for the asserted conclusion.',

                'supporting_quote':
                    'therefore X is true',

                'charitable_reading':
                    'The speaker may mean X is widely accepted.',
            }

        elif role == 'ARSArbiter':
            value = {
                'validated_dimensions': {
                    'acceptability':
                        'supported',

                    'relevance':
                        'unsupported',

                    'sufficiency':
                        'unsupported',
                },

                'candidate_type':
                    'Appeal to Majority',

                'nearest_competitor':
                    'Hasty Generalization',

                'mapping_reason':
                    (
                        'Popularity is used as justification '
                        'for truth rather than as a sample '
                        'for population generalization.'
                    ),

                'prediction':
                    'Fallacious',

                'content':
                    'The target instantiates a closed-set pattern.',
            }

        else:
            raise AssertionError(
                f'Unexpected role: {role}'
            )

        if metadata['stage'] == 'ars_review':
            value = {
                'review_action':
                    'keep',

                'peer_effect':
                    (
                        'No peer report defeats '
                        'this dimension finding.'
                    ),

                **value,
            }

        validate_output(
            value,
            schema,
        )

        if validator is not None:
            validator(value)

        return value
```

---

# 37. Test ARS role constants

Add:

```python
def test_ars_roles_are_distinct():
    assert ARS_ROLES == (
        'Acceptability',
        'Relevance',
        'Sufficiency',
    )
```

---

# 38. Test call count for no-debate

Add:

```python
def test_ars_no_debate_has_five_calls():
    llm = ARSTestLLM()

    engine = Engine(
        llm,
        task='detection',
        mode='adaptive',
        adaptive_policy='ars_no_debate',
    )

    result = engine.run(
        ModelInput(
            '',
            '',
            TARGET,
        ),
        {
            'sample_id':
                'ars:test',
        },
    )

    roles = [
        call['metadata']['role']
        for call in llm.calls
    ]

    assert roles == [
        'ARSArgumentDecomposer',
        'Acceptability',
        'Relevance',
        'Sufficiency',
        'ARSArbiter',
    ]

    assert result['framework'] == 'ARS'
```

---

# 39. Test only Arbiter sees label names

Add:

```python
def test_only_ars_arbiter_sees_labels():
    llm = ARSTestLLM()

    engine = Engine(
        llm,
        task='detection',
        mode='adaptive',
        adaptive_policy='ars_no_debate',
    )

    engine.run(
        ModelInput(
            '',
            '',
            TARGET,
        ),
        {},
    )

    forbidden = (
        'Appeal to Authority',
        'Appeal to Majority',
        'Appeal to Nature',
        'Appeal to Tradition',
        'Appeal to Worse Problems',
        'False Dilemma',
        'Hasty Generalization',
        'Slippery Slope',
        'Fallacious',
        'Non-Fallacious',
    )

    for call in llm.calls:
        role = (
            call['metadata']['role']
        )

        prompt = (
            call['system_prompt']
        )

        if role == 'ARSArbiter':
            continue

        for term in forbidden:
            assert term not in prompt
```

This test is extremely important.

It proves the architecture actually satisfies:

```text
specialists diagnose
arbiter classifies
```

---

# 40. Test independent specialists

Add:

```python
def test_ars_initial_agents_are_independent():
    llm = ARSTestLLM()

    engine = Engine(
        llm,
        task='detection',
        mode='adaptive',
        adaptive_policy='ars_no_debate',
    )

    engine.run(
        ModelInput(
            '',
            '',
            TARGET,
        ),
        {},
    )

    initial_calls = [
        call
        for call in llm.calls
        if (
            call['metadata']['stage']
            == 'ars_initial'
        )
    ]

    assert len(initial_calls) == 3

    for call in initial_calls:
        assert (
            call['payload']['reports']
            == {}
        )

        assert (
            call['payload']['history']
            == []
        )
```

---

# 41. Test synchronous review

Add:

```python
def test_ars_review_is_synchronous():
    llm = ARSTestLLM()

    engine = Engine(
        llm,
        task='detection',
        mode='adaptive',
        adaptive_policy='ars_review',
    )

    result = engine.run(
        ModelInput(
            '',
            '',
            TARGET,
        ),
        {},
    )

    review_calls = [
        call
        for call in llm.calls
        if (
            call['metadata']['stage']
            == 'ars_review'
        )
    ]

    assert len(llm.calls) == 8

    assert len(review_calls) == 3

    for call in review_calls:
        assert (
            call['payload']['reports']
            == result['initial_diagnoses']
        )

        assert (
            call['payload']['history']
            == []
        )
```

---

# 42. Test Arbiter sees only final diagnoses

Add:

```python
def test_ars_arbiter_sees_final_only():
    llm = ARSTestLLM()

    engine = Engine(
        llm,
        task='detection',
        mode='adaptive',
        adaptive_policy='ars_review',
    )

    result = engine.run(
        ModelInput(
            '',
            '',
            TARGET,
        ),
        {},
    )

    arbiter_call = next(
        call
        for call in llm.calls
        if (
            call['metadata']['role']
            == 'ARSArbiter'
        )
    )

    assert (
        arbiter_call['payload']['reports']
        == {
            'final_diagnoses':
                result['final_diagnoses']
        }
    )

    assert (
        arbiter_call['payload']['history']
        == []
    )
```

---

# 43. Test label leakage validator

Add:

```python
def test_label_leakage_is_rejected():
    from src.ars_schemas import (
        validate_label_agnostic,
    )

    with pytest.raises(ValueError):
        validate_label_agnostic({
            'finding':
                'This is Appeal to Majority.',

            'supporting_quote':
                'Many people believe X',
        })
```

Then allow verbatim quote:

```python
def test_label_name_inside_quote_is_allowed():
    from src.ars_schemas import (
        validate_label_agnostic,
    )

    validate_label_agnostic({
        'finding':
            'The speaker explicitly names a concept.',

        'supporting_quote':
            'This is a slippery slope',
    })
```

---

# 44. Test decomposition provenance

Add:

```python
def test_decomposition_claim_must_be_verbatim():
    from src.ars_schemas import (
        validate_ars_decomposition,
    )

    value = {
        'argumentative_status':
            'explicit_argument',

        'claims': [
            {
                'id': 'C1',
                'source': 'target_comment',
                'role': 'premise',
                'text': 'invented paraphrase',
                'qualifiers': [],
                'modality': 'asserted',
            }
        ],

        'main_conclusion_id':
            None,

        'implicit_assumptions':
            [],

        'inference_links':
            [],

        'scope_notes':
            [],

        'uncertainty':
            [],
    }

    with pytest.raises(ValueError):
        validate_ars_decomposition(
            value,
            {
                'title': '',
                'parent_comment': '',
                'comment': TARGET,
            },
        )
```

---

# 45. Test Arbiter consistency

Add:

```python
def test_detection_candidate_none_requires_nonfallacious():
    from src.ars_schemas import (
        validate_ars_arbiter,
    )

    value = {
        'validated_dimensions': {
            'acceptability':
                'supported',

            'relevance':
                'supported',

            'sufficiency':
                'supported',
        },

        'candidate_type':
            'None',

        'nearest_competitor':
            'Appeal to Majority',

        'mapping_reason':
            'No benchmark class is established.',

        'prediction':
            'Fallacious',

        'content':
            'x',
    }

    with pytest.raises(ValueError):
        validate_ars_arbiter(
            value,
            'detection',
        )
```

---

# 46. Run new tests

Run:

```bash
pytest tests/test_ars_diagnostic.py -v
```

Do not proceed until all new tests pass.

---

# 47. Run regression tests

Then:

```bash
pytest tests/test_engine.py -v
```

Then:

```bash
pytest tests/test_adaptive_review.py -v
```

Then:

```bash
pytest -q
```

Requirement:

```text
ALL OLD TESTS PASS
ALL NEW TESTS PASS
```

If an old test fails, fix integration instead of changing old test expectations.

---

# 48. Create detection config

Create:

```text
configs/detection.ars_no_debate.yaml
```

Copy current:

```text
configs/detection.diagnostic_no_debate.yaml
```

Then change only:

```yaml
engine:
  adaptive_policy: ars_no_debate
```

and:

```yaml
output_dir: outputs/nvidia-detection-ars-no-debate-dev-v1
```

Recommended full file:

```yaml
task: detection
data_dir: data/cocolofa
split: dev
context: paper

engine:
  mode: adaptive
  protocol: round_robin
  max_rounds: 1
  early_stop: false
  adaptive_policy: ars_no_debate

model:
  provider: openai_compatible
  name: openai/gpt-oss-20b
  base_url: https://integrate.api.nvidia.com/v1
  api_key_env: NVIDIA_API_KEY
  temperature: 1.0
  max_completion_tokens: 2048
  timeout_seconds: 120
  max_attempts: 3
  backoff_seconds: 1
  structured_output: true
  input_cost_per_million: null
  output_cost_per_million: null
  cached_input_cost_per_million: null

output_dir: outputs/nvidia-detection-ars-no-debate-dev-v1

cache_dir: cache/ars-v1
```

---

# 49. Create detection review config

Create:

```text
configs/detection.ars.yaml
```

Same config except:

```yaml
adaptive_policy: ars_review
```

and:

```yaml
output_dir: outputs/nvidia-detection-ars-review-dev-v1
```

---

# 50. Create classification configs

Create:

```text
configs/classification.ars_no_debate.yaml
configs/classification.ars.yaml
```

Same changes:

```yaml
task: classification
```

For no-debate:

```yaml
adaptive_policy: ars_no_debate
```

For review:

```yaml
adaptive_policy: ars_review
```

---

# 51. Do NOT reuse cached stochastic outputs

Current model:

```yaml
temperature: 1.0
```

If you want a new independent run, use:

```text
cache/ars-v1-run1
cache/ars-v1-run2
cache/ars-v1-run3
```

Do not only change:

```text
output_dir
```

because identical prompts may be replayed from response cache.

---

# 52. Run mock smoke test

First:

```bash
python -m src.run_detection \
  --config configs/detection.ars_no_debate.yaml \
  --mock \
  --limit 3 \
  --output outputs/mock-detection-ars-no-debate
```

Then:

```bash
python -m src.run_detection \
  --config configs/detection.ars.yaml \
  --mock \
  --limit 3 \
  --output outputs/mock-detection-ars-review
```

Expected:

```text
status = complete
```

---

# 53. Inspect generated trace

For `ars_no_debate`, expected shape:

```json
{
  "framework": "ARS",

  "decomposition": {},

  "initial_diagnoses": {
    "Acceptability": {},
    "Relevance": {},
    "Sufficiency": {}
  },

  "diagnostic_review": [],

  "final_diagnoses": {
    "Acceptability": {},
    "Relevance": {},
    "Sufficiency": {}
  },

  "arbiter": {
    "validated_dimensions": {},
    "candidate_type": "...",
    "nearest_competitor": "...",
    "mapping_reason": "...",
    "prediction": "...",
    "content": "..."
  },

  "prediction": "...",

  "stop_reason": "ars_no_debate"
}
```

---

# 54. First real test: inspect known failure sample

Start with previously inspected sample:

```text
237:5507
```

Do not tune prompt to force:

```text
Non-Fallacious
```

Instead inspect:

```text
1. Did Decomposer preserve "might"?

2. Did Acceptability stay in acceptability?

3. Did Relevance stay in relevance?

4. Did Sufficiency stay in sufficiency?

5. Did any specialist mention a class name?

6. Did Arbiter invent a class not grounded in diagnoses?

7. Did Arbiter confuse a general reasoning weakness
   with one of the eight annotated benchmark classes?
```

The goal is diagnosis of failure source.

---

# 55. How the same sample should conceptually look

For a normative rights comment, a plausible trace may be:

```text
Acceptability:
not_applicable / satisfied

Relevance:
satisfied

Sufficiency:
satisfied or uncertain
```

Then Arbiter may choose:

```text
candidate_type=None
prediction=Non-Fallacious
```

But do not hard-code this logic for one sample.

---

# 56. Experimental matrix

Use exactly the same dev sample IDs:

```text
A. single

B. no_deliberation

C. diagnostic_no_debate

D. diagnostic_review

E. ars_no_debate

F. ars_review
```

---

# 57. Key comparison 1

```text
C vs E
```

Tests:

```text
Does theory-grounded ARS role decomposition
outperform Inference/Evidence/SemanticContext?
```

---

# 58. Key comparison 2

```text
E vs F
```

Tests:

```text
Does role-preserving review improve
ARS diagnoses?
```

Measure:

```text
wrong -> correct

correct -> wrong

net_review_gain
=
wrong_to_correct
-
correct_to_wrong
```

---

# 59. Key comparison 3

```text
A vs E/F
```

Question:

```text
Is the multi-agent cost actually justified?
```

---

# 60. Detection metrics

Track:

```text
Accuracy
Precision
Recall
F1
False Positive Count
False Positive Rate
```

False Positive Rate is especially important because previous deliberation already produced false-positive amplification.

---

# 61. Classification metrics

Track:

```text
Accuracy
Macro-F1
Per-class F1
Confusion matrix
```

Especially inspect:

```text
Hasty Generalization
vs
Slippery Slope

Appeal to Majority
vs
Hasty Generalization

False Dilemma
vs
other insufficiency errors
```

---

# 62. Do not implement selective review yet

V1 should compare:

```text
ars_no_debate
vs
ars_review
```

cleanly.

Only after `ars_review` shows positive net gain should you create:

```text
ars_selective_review
```

Possible V2 triggers:

```text
multiple specialists corrected decomposition

dimension_status=uncertain

A/R/S conflict

arbiter nearest competitor is close

arbiter confidence low
```

But not now.

---

# 63. Documentation file

Create:

```text
docs/ARS_DIAGNOSTIC_V1.md
```

Use:

```markdown
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

- ars_no_debate
- ars_review

## Baselines retained

- diagnostic_no_debate
- diagnostic_review
- legacy planner/debate
- single
```

---

# 64. Recommended commit sequence

Commit 1:

```bash
git add src/labels.py
git commit -m "feat: add ARS role constants"
```

Commit 2:

```bash
git add src/ars_schemas.py tests/test_ars_diagnostic.py
git commit -m "feat: add ARS schemas and validators"
```

Commit 3:

```bash
git add src/ars_prompts.py
git commit -m "feat: add label-agnostic ARS prompts"
```

Commit 4:

```bash
git add src/ars_diagnostic.py
git commit -m "feat: add ARS diagnostic executor"
```

Commit 5:

```bash
git add src/engine.py
git commit -m "feat: route ARS policies through engine"
```

Commit 6:

```bash
git add configs
git commit -m "chore: add ARS experiment configs"
```

Commit 7:

```bash
git add docs/ARS_DIAGNOSTIC_V1.md README.md
git commit -m "docs: document ARS diagnostic architecture"
```

---

# 65. Final verification checklist

Before any real API benchmark:

```text
[ ] ARSArgumentDecomposer prompt contains no fallacy label names

[ ] Acceptability prompt contains no fallacy label names

[ ] Relevance prompt contains no fallacy label names

[ ] Sufficiency prompt contains no fallacy label names

[ ] ARS review prompt contains no fallacy label names

[ ] Only ARSArbiter sees labels

[ ] Decomposer claims are verbatim in declared source

[ ] Decomposer preserves qualifiers/modality

[ ] Specialist can reject/correct decomposition

[ ] Acceptability can return not_applicable

[ ] Relevance cannot judge premise truth

[ ] Sufficiency cannot judge premise truth

[ ] Initial specialist calls receive reports={}

[ ] Review calls receive identical frozen initial reports

[ ] Review calls receive history=[]

[ ] Arbiter receives final diagnoses only

[ ] ars_no_debate = 5 calls/sample

[ ] ars_review = 8 calls/sample

[ ] old diagnostic tests still pass

[ ] legacy engine tests still pass

[ ] full pytest suite passes
```

---

# 66. What NOT to do

Do not do this:

```text
rename Inference -> Sufficiency
rename Evidence -> Acceptability
rename Semantic -> Relevance
```

That is only cosmetic.

The real change is:

```text
old diagnostic:
specialist can reason toward fallacy candidates

new ARS:
specialist produces only an argument-quality dimension diagnosis
```

---

# 67. The most important implementation difference

Old detection flow:

```text
specialist
-> candidate_type
-> supported/rejected
-> hard gate
-> arbiter
```

New ARS flow:

```text
specialist
-> satisfied/violated/uncertain/not_applicable
-> no candidate type
-> arbiter alone maps A/R/S pattern to CoCoLoFa class
```

That is the actual architectural change.

---

# 68. Recommended execution order

Follow exactly:

```text
1. labels.py

2. ars_schemas.py

3. schema validators

4. tests for schemas

5. ars_prompts.py

6. label visibility test

7. ars_diagnostic.py

8. engine.py

9. call-count tests

10. synchronous-review tests

11. full regression tests

12. config files

13. mock run

14. small real dev run

15. inspect traces

16. ars_no_debate paired comparison

17. ars_review paired comparison

18. full dev only after architecture is stable

19. freeze

20. test split
```

Do not change prompts after looking at test labels.
