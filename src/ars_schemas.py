from src.labels import DETECTION, FALLACIES
from src.schemas import object_schema, validate_output


DIMENSION_STATUS = (
    'satisfied',
    'violated',
    'uncertain',
    'not_applicable',
)


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


def ars_diagnosis_schema(role):
    mapping = {
        'Acceptability': acceptability_schema,
        'Relevance': relevance_schema,
        'Sufficiency': sufficiency_schema,
    }

    if role not in mapping:
        raise ValueError(f'Unknown ARS role: {role}')

    return mapping[role]()


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


def validate_ars_arbiter(value, task):
    validate_output(value, ars_arbiter_schema(task))

    if task == 'detection':
        candidate = value['candidate_type']
        prediction = value['prediction']

        if candidate == 'None':
            if prediction != 'Non-Fallacious':
                raise ValueError(
                    'candidate_type=None requires Non-Fallacious'
                )
        elif prediction != 'Fallacious':
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


def validate_ars_decomposition(value, input_dict):
    validate_output(value, ars_argument_schema())

    claims = value['claims']
    claim_ids = [claim['id'] for claim in claims]

    if len(claim_ids) != len(set(claim_ids)):
        raise ValueError('Claim IDs must be unique')

    claims_by_id = {claim['id']: claim for claim in claims}
    assumption_ids = {
        assumption['id']
        for assumption in value['implicit_assumptions']
    }
    all_ids = set(claims_by_id) | assumption_ids
    main_conclusion_id = value['main_conclusion_id']

    if (
        main_conclusion_id is not None
        and main_conclusion_id not in claims_by_id
    ):
        raise ValueError('main_conclusion_id must reference a claim')

    for link in value['inference_links']:
        for source_id in link['from']:
            if source_id not in all_ids:
                raise ValueError(f'Unknown inference source: {source_id}')

        target_id = link['to']
        if target_id is not None and target_id not in all_ids:
            raise ValueError(f'Unknown inference target: {target_id}')

    source_text = {
        'title': input_dict.get('title', ''),
        'article': input_dict.get('article', '') or '',
        'parent_comment': input_dict.get('parent_comment', ''),
        'target_comment': input_dict.get('comment', ''),
    }

    for claim in claims:
        declared_source = claim['source']
        claim_text = claim['text']
        if claim_text not in source_text[declared_source]:
            raise ValueError(
                f"Claim {claim['id']} must be verbatim in "
                f"declared source {declared_source}"
            )


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


def _generated_strings(value):
    if isinstance(value, dict):
        for key, subvalue in value.items():
            if key in {'text', 'supporting_quote'}:
                continue
            yield from _generated_strings(subvalue)
    elif isinstance(value, list):
        for item in value:
            yield from _generated_strings(item)
    elif isinstance(value, str):
        yield value


def validate_label_agnostic(value):
    generated_text = ' '.join(_generated_strings(value)).casefold()

    for term in FORBIDDEN_GENERATED_TERMS:
        if term in generated_text:
            raise ValueError(
                'Label-aware language is forbidden before arbitration: '
                f'{term}'
            )


def _normalize_text(text):
    return ' '.join(text.split()).casefold()


def validate_target_quote(value, target_comment):
    quote = _normalize_text(value['supporting_quote'])
    target = _normalize_text(target_comment)

    if not quote:
        raise ValueError('supporting_quote must not be empty')

    if quote not in target:
        raise ValueError(
            'supporting_quote must occur verbatim in target comment'
        )


def validate_ars_diagnosis(value, role, target_comment):
    validate_output(value, ars_diagnosis_schema(role))
    validate_label_agnostic(value)
    validate_target_quote(value, target_comment)


def validate_ars_review(value, role, target_comment):
    validate_output(value, ars_review_schema(role))
    validate_label_agnostic(value)
    validate_target_quote(value, target_comment)
