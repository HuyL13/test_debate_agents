from copy import deepcopy

from src.protocols.common import stable, team_gap


def execute(ask, initial, plan, task, early_stop):
    reports, history, previous = deepcopy(initial), [], None
    hypotheses = {side: list(dict.fromkeys(initial[r]['prediction'] for r in plan[side]))
                  for side in ('affirmative', 'negative')}
    for round_index in range(plan['max_rounds']):
        for side in ('affirmative', 'negative'):
            for role in plan[side]:
                output = ask(role, f'pc_{round_index}_{side}', reports, history,
                             f'You are on the {side} team. Defend its initial assessment(s) '
                             f'{hypotheses[side]} against the other team. Rebut specific arguments '
                             'using supplied text. You may concede and revise when warranted; '
                             'your prediction must be your honest current assessment.')
                reports[role] = output
                history.append({'round': round_index, 'role': role, 'side': side, 'kind': 'rebuttal', **output})
        if early_stop:
            if team_gap(reports, plan['affirmative'], plan['negative'], task) < 0.2:
                return reports, history, 'convergence'
            if previous is not None and all(stable(reports, previous, plan[side], task)
                                            for side in ('affirmative', 'negative')):
                return reports, history, 'stagnation'
        previous = deepcopy(reports)
    return reports, history, 'max_rounds'
