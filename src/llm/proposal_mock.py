"""Contract fixtures only: no claims about linguistic or benchmark performance."""
from src.labels import FALLACIES


def assessment(label, quote, supported=True):
    return {'class': label, 'condition_status': 'supported' if supported else 'not_established',
            'inference_role': 'primary' if supported else 'unresolved',
            'defining_condition': 'OFFLINE fixture condition, not a semantic judgment.',
            'missing_condition': '' if supported else 'OFFLINE fixture does not establish this condition.',
            'premise_quote': quote if supported else '', 'conclusion_quote': quote if supported else '',
            'evidence_quote': quote if supported else '', 'explanation': 'OFFLINE contract fixture.'}


def inference(quote):
    return {'premise_quote': quote, 'conclusion_quote': quote,
            'disputed_step': 'OFFLINE mock step, not linguistic analysis.',
            'implicit_warrant': '', 'warrant_basis': 'explicit'}


def response(schema, user, seed):
    properties = schema['properties']
    quote = user['input']['comment'][:220]
    reports = user['reports']
    if 'ranking_reason' in properties:
        candidate = FALLACIES[seed % len(FALLACIES)]
        rival = next(c for c in FALLACIES if c != candidate)
        return {'has_fallacy_charge': True, 'candidate_class': candidate, 'quote': quote,
                'defect_mechanism': 'OFFLINE candidate fixture.', 'runner_up_class': rival,
                'runner_up_defect': 'OFFLINE weaker rival fixture.', 'runner_up_quote': '',
                'inference': inference(quote), 'candidate_assessment': assessment(candidate, quote),
                'runner_up_assessment': assessment(rival, quote, False), 'ranking_reason': 'OFFLINE ranking.'}
    if 'candidate_assessment' in properties:
        candidate = reports['prosecutor_indictment']['candidate_class']
        return {'decision': 'uphold', 'inference': inference(quote),
                'candidate_assessment': assessment(candidate, quote),
                'alternative_assessment': assessment('None', quote, False),
                'candidate_objection': '', 'decisive_difference': 'OFFLINE no supported rival.',
                'unresolved_commitment': '', 'comparison': 'OFFLINE uphold contract fixture.'}
    options = reports['options']
    return {'prediction': options[0]['class'], 'confidence': 0.5, 'content': 'OFFLINE forced choice.',
            'selection_reason': 'OFFLINE fixture selection.', 'rejected_reason': 'OFFLINE limitations.',
            'resolution': 'selected', 'option_assessments': [assessment(o['class'], quote) for o in options]}
