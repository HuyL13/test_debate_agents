from copy import deepcopy

from src.protocols.common import distance, stable


def execute(ask, initial, plan, task, early_stop):
    reports, history, previous = deepcopy(initial), [], None
    for round_index in range(plan['max_rounds']):
        for role in plan['order']:
            output = ask(role, f'rr_{round_index}', reports, history,
                         'Respond to the previous speaker. Identify a specific missed premise, '
                         'correction or contextual limitation rather than merely agreeing.')
            reports[role] = output
            history.append({'round': round_index, 'role': role, 'kind': 'revision', **output})
        if early_stop and previous is not None:
            same_label = len({r['prediction'] for r in reports.values()}) == 1
            spread = max(distance(reports[a], reports[b], task) for a in reports for b in reports)
            if same_label and (spread < 0.15 or all(r['confidence'] > 0.8 for r in reports.values())):
                return reports, history, 'consensus'
            if stable(reports, previous, plan['order'], task):
                return reports, history, 'stagnation'
        previous = deepcopy(reports)
    return reports, history, 'max_rounds'
