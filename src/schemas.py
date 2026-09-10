import math
from itertools import permutations

from jsonschema import Draft202012Validator

from src.labels import FALLACIES, PROTOCOLS, ROLES, labels_for


def object_schema(properties):
    return {'type': 'object', 'properties': properties,
            'required': list(properties), 'additionalProperties': False}


def report_schema(task):
    return object_schema({'prediction': {'type': 'string', 'enum': list(labels_for(task))},
                          'confidence': {'type': 'number', 'minimum': 0, 'maximum': 1},
                          'content': {'type': 'string'}})


QUESTION_SCHEMA = object_schema({'question': {'type': ['string', 'null']}, 'content': {'type': 'string'}})


def argument_schema():
    claim = object_schema({'id': {'type': 'string', 'minLength': 1},
                           'source': {'type': 'string',
                                      'enum': ['title', 'article', 'parent_comment', 'target_comment']},
                           'role': {'type': 'string',
                                    'enum': ['premise', 'conclusion', 'evidence', 'background', 'other']},
                           'text': {'type': 'string', 'maxLength': 240}})
    return object_schema({'argumentative_status': {'type': 'string',
                                                   'enum': ['explicit_argument', 'implicit_argument', 'assertion',
                                                            'question', 'sarcasm', 'fragment', 'unclear']},
                          'claims': {'type': 'array', 'items': claim, 'maxItems': 4},
                          'conclusion_id': {'type': ['string', 'null'], 'maxLength': 24},
                          'implicit_assumptions': {'type': 'array', 'items': {'type': 'string', 'maxLength': 180},
                                                   'maxItems': 3},
                          'reasoning_relation': {'type': 'string', 'maxLength': 320},
                          'scope_notes': {'type': 'array', 'items': {'type': 'string', 'maxLength': 180},
                                          'maxItems': 3},
                          'uncertainty': {'type': 'array', 'items': {'type': 'string', 'maxLength': 180},
                                          'maxItems': 3}})


def diagnosis_schema(role):
    return object_schema({'issue_status': {'type': 'string', 'enum': ['present', 'absent', 'uncertain']},
                          'diagnosis': {'type': 'string', 'maxLength': 360},
                          'supporting_quote': {'type': 'string', 'minLength': 1, 'maxLength': 220},
                          'structure_objection': {'type': 'string', 'maxLength': 260},
                          'alternative_interpretation': {'type': 'string', 'maxLength': 260}})


def detection_candidate_schema(role):
    return object_schema({'candidate_type': {'type': 'string', 'enum': [*FALLACIES, 'None']},
                          'status': {'type': 'string', 'enum': ['supported', 'rejected']},
                          'necessary_conditions_met': {'type': 'boolean'},
                          'sufficient_evidence': {'type': 'boolean'},
                          'supporting_quote': {'type': 'string', 'minLength': 1, 'maxLength': 220},
                          'premise': {'type': 'string', 'maxLength': 220},
                          'conclusion': {'type': 'string', 'maxLength': 220},
                          'defective_inference': {'type': 'string', 'maxLength': 320},
                          'strongest_nonfallacious_reading': {'type': 'string', 'maxLength': 320},
                          'auxiliary_observation': {'type': 'string', 'maxLength': 260}})


def diagnostic_review_schema(role):
    return object_schema({'decision': {'type': 'string', 'enum': ['keep', 'revise', 'withdraw']},
                          'diagnosis': {'type': 'string', 'maxLength': 360},
                          'supporting_quote': {'type': 'string', 'minLength': 1, 'maxLength': 220},
                          'response_to_other_diagnoses': {'type': 'string', 'maxLength': 360},
                          'remaining_uncertainty': {'type': 'string', 'maxLength': 220}})


def review_schema(task):
    properties = report_schema(task)['properties']
    return object_schema({**properties, 'supporting_quote': {'type': 'string', 'minLength': 1}})


def _normalize_quote_text(text):
    for dash in ('\u2010', '\u2011', '\u2012', '\u2013', '\u2014', '\u2212'):
        text = text.replace(dash, '-')
    for quote in ('\u2018', '\u2019', '\u201a', '\u201b'):
        text = text.replace(quote, "'")
    for quote in ('\u201c', '\u201d', '\u201e', '\u201f'):
        text = text.replace(quote, '"')
    return ' '.join(text.split())


def validate_target_quote(value, target):
    quote = _normalize_quote_text(value['supporting_quote'])
    if not quote or quote.casefold() not in _normalize_quote_text(target).casefold():
        raise ValueError('supporting_quote must be a nonempty verbatim span from the target comment')


def validate_review_quote(value, target):
    validate_target_quote(value, target)


def plan_schema(max_rounds, initial=None):
    role_list = {'type': 'array', 'items': {'type': 'string', 'enum': list(ROLES)}}
    schema = object_schema({'protocol': {'type': 'string', 'enum': list(PROTOCOLS)},
                          'topic': {'type': 'string'}, 'reason': {'type': 'string'},
                          'order': role_list, 'affirmative': role_list, 'negative': role_list,
                          'examiner': {'type': 'string', 'enum': list(ROLES)},
                          'max_rounds': {'type': 'integer', 'minimum': 1, 'maximum': max_rounds}})
    if initial is not None:
        properties = schema['properties']
        properties['order'] = {**role_list, 'enum': [list(order) for order in permutations(ROLES)]}
        groups = {}
        for role in ROLES:
            groups.setdefault(initial[role]['prediction'], []).append(role)
        teams = list(groups.values()) if len(groups) == 2 else [[], []]
        properties['affirmative'] = {**role_list, 'enum': [teams[0]]}
        properties['negative'] = {**role_list, 'enum': [teams[1]]}
        if len(groups) != 2:
            properties['protocol']['enum'].remove('point_counterpoint')
    return schema


def validate_output(value, schema):
    def finite(item):
        if isinstance(item, float) and not math.isfinite(item):
            raise ValueError('Non-finite JSON number')
        if isinstance(item, dict):
            for sub in item.values():
                finite(sub)
        elif isinstance(item, list):
            for sub in item:
                finite(sub)
    finite(value)
    errors = list(Draft202012Validator(schema).iter_errors(value))
    if errors:
        raise ValueError('Output does not match schema: ' + errors[0].message)


def validate_plan(plan, max_rounds, initial=None):
    validate_output(plan, plan_schema(max_rounds))
    if len(plan['order']) != 3 or set(plan['order']) != set(ROLES):
        raise ValueError('Order must include each role once')
    a, b = plan['affirmative'], plan['negative']
    if plan['protocol'] == 'point_counterpoint' and (
            sorted([len(a), len(b)]) != [1, 2] or len(set(a + b)) != 3 or set(a + b) != set(ROLES)):
        raise ValueError('Teams must be a disjoint 2v1 partition of all roles')
    if not plan['topic'].strip() or not plan['reason'].strip():
        raise ValueError('Planner must state topic and reason')
    if initial is not None and plan['protocol'] == 'point_counterpoint':
        if len({report['prediction'] for report in initial.values()}) != 2:
            raise ValueError('Adaptive point-counterpoint requires two natural prediction groups')
        if any(len({initial[r]['prediction'] for r in team}) != 1 for team in (a, b)):
            raise ValueError('Adaptive teams must follow the initial prediction groups')
