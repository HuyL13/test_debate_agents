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


def execute(ask, model_input, policy):
    decomposition = ask(
        'ARSArgumentDecomposer',
        'ars_decomposition',
        {},
        [],
        'Extract a label-agnostic structured argument representation.',
        schema=ars_argument_schema(),
        validator=lambda value: validate_ars_decomposition(
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
            f'Provide an independent {role} diagnosis only.',
            schema=ars_diagnosis_schema(role),
            validator=lambda value, role=role: validate_ars_diagnosis(
                value,
                role,
                model_input.comment,
            ),
            extra={'decomposition': decomposition},
        )

    final = deepcopy(initial)
    reviews = []
    reason = 'ars_no_debate'

    if policy == 'ars_review':
        frozen_initial = deepcopy(initial)

        for role in ARS_ROLES:
            output = ask(
                role,
                'ars_review',
                frozen_initial,
                [],
                (
                    'Review your own ARS dimension using the immutable '
                    'initial diagnoses. Other dimensions may expose a '
                    'weakness in your analysis, but remain inside your own '
                    'assigned dimension. Return keep, revise or withdraw. '
                    'Do not classify the target.'
                ),
                schema=ars_review_schema(role),
                validator=lambda value, role=role: validate_ars_review(
                    value,
                    role,
                    model_input.comment,
                ),
                extra={'decomposition': decomposition},
            )

            final[role] = output
            reviews.append({
                'round': 0,
                'role': role,
                'kind': 'ars_review',
                **output,
            })

        reason = 'ars_review'

    return decomposition, initial, reviews, final, reason
