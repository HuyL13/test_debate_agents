import math
from itertools import permutations

from jsonschema import Draft202012Validator

from src.labels import PROTOCOLS, ROLES, labels_for


def object_schema(properties):
    return {'type': 'object', 'properties': properties,
            'required': list(properties), 'additionalProperties': False}


def report_schema(task):
    return object_schema({'prediction': {'type': 'string', 'enum': list(labels_for(task))},
                          'confidence': {'type': 'number', 'minimum': 0, 'maximum': 1},
                          'content': {'type': 'string'}})


QUESTION_SCHEMA = object_schema({'question': {'type': ['string', 'null']}, 'content': {'type': 'string'}})


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
