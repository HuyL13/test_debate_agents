from copy import deepcopy

from src.labels import DIAGNOSTIC_ROLES, FALLACIES
from src.schemas import argument_schema, detection_candidate_schema, diagnosis_schema, diagnostic_review_schema


def aggregate_detection_candidates(diagnoses):
    candidates = []
    for role, diagnosis in diagnoses.items():
        candidate = {**diagnosis, 'source_agent': role}
        candidates.append(candidate)
    supported = [
        candidate for candidate in candidates
        if candidate.get('candidate_type') in FALLACIES
        and candidate.get('status') == 'supported'
        and candidate.get('necessary_conditions_met') is True
        and candidate.get('sufficient_evidence') is True
    ]
    return {'prediction': None if supported else 'Non-Fallacious',
            'candidate_types_proposed': sorted({
                candidate.get('candidate_type') for candidate in candidates
                if candidate.get('candidate_type') in FALLACIES
            }),
            'candidate_types_supported': sorted({
                candidate['candidate_type'] for candidate in supported
            }),
            'candidate_types_rejected_by_skeptic': [],
            'final_verified_candidate': supported[0]['candidate_type'] if supported else None,
            'hard_gate_reason': 'supported_closed_set_candidate' if supported else 'no_supported_closed_set_candidate',
            'nonfallacious_default_used': not supported,
            'candidates': candidates}


def execute(ask, model_input, policy, task):
    decomposition = ask('ArgumentDecomposer', 'decomposition', {}, [],
                        'Decompose the target argument without predicting any task label.',
                        schema=argument_schema())
    initial = {}
    schema_factory = detection_candidate_schema if task == 'detection' else diagnosis_schema
    diagnostic_instruction = (
        'Propose or reject exactly one closed-set CoCoLoFa candidate for your assigned diagnostic role. '
        'Use status supported only when the target text itself establishes the defining inference. '
        'If evidence is ambiguous, incomplete, insufficient, or outside the eight target classes, use rejected. '
        'Do not output uncertain or abstain. Include a nonempty verbatim supporting_quote from the target comment.'
        if task == 'detection' else
        'Provide an independent role-specific diagnosis. Do not predict a task label. '
        'Include a nonempty verbatim supporting_quote from the target comment.')
    for role in DIAGNOSTIC_ROLES:
        initial[role] = ask(role, 'diagnostic_initial', {}, [],
                            diagnostic_instruction,
                            schema=schema_factory(role),
                            extra={'decomposition': decomposition, 'diagnoses': {}})
    reviews = []
    final = deepcopy(initial)
    reason = 'diagnostic_no_debate'
    if policy == 'diagnostic_review':
        frozen = deepcopy(initial)
        for role in DIAGNOSTIC_ROLES:
            review_schema = detection_candidate_schema(role) if task == 'detection' else diagnostic_review_schema(role)
            review_instruction = (
                'Review immutable initial closed-set candidates while staying within your assigned reasoning dimension. '
                'Return supported only when the target text itself establishes a valid CoCoLoFa candidate; otherwise '
                'return rejected. Do not output uncertain or abstain. Include a nonempty verbatim supporting_quote '
                'from the target comment.'
                if task == 'detection' else
                'Review immutable initial diagnoses while staying within your assigned reasoning dimension. Use other '
                'diagnoses only to check whether they expose a weakness in your own diagnosis. Do not predict a task '
                'label. Include a nonempty verbatim supporting_quote from the target comment.')
            output = ask(role, 'diagnostic_review', frozen, [],
                         review_instruction,
                         schema=review_schema,
                         extra={'decomposition': decomposition, 'diagnoses': frozen})
            final[role] = output
            reviews.append({'round': 0, 'role': role, 'kind': 'diagnostic_review', **output})
        reason = 'diagnostic_review'
    aggregation = aggregate_detection_candidates(final) if task == 'detection' else None
    return decomposition, initial, reviews, final, reason, aggregation
