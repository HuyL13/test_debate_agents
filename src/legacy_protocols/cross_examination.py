from copy import deepcopy

from src.legacy_protocols.common import stable
from src.schemas import QUESTION_SCHEMA


def execute(ask, initial, plan, task, early_stop):
    reports, history, previous, seen = deepcopy(initial), [], None, set()
    examiner = plan['examiner']
    respondents = [r for r in plan['order'] if r != examiner]
    question = None
    for round_index in range(plan['max_rounds']):
        if question is None:
            question_output = ask(examiner, f'ce_{round_index}_question', reports, history,
                                  'Ask a targeted question exposing a contradiction or unsupported premise. '
                                  'Write an actual interrogative about a specific inference in the reports; '
                                  'do not copy the target comment as the question. Test a competing '
                                  'interpretation rather than asking others to confirm consensus. '
                                  'Use null only if there is no unresolved question.', schema=QUESTION_SCHEMA)
            question = question_output['question']
        else:
            question_output = {'question': question, 'content': 'Follow-up from examiner reflection.'}
        history.append({'round': round_index, 'role': examiner, 'kind': 'question', **question_output})
        normalized = question.strip().casefold() if question else ''
        if early_stop and (not normalized or normalized in seen):
            return reports, history, 'information_saturation'
        if not normalized:
            question = 'Which unresolved premise most affects your prediction?'
        seen.add(normalized)
        for role in respondents:
            output = ask(role, f'ce_answer_{round_index}', reports, history,
                         'Answer the examiner directly. Cite supplied text and admit uncertainty '
                         'or correct your assessment when the question reveals a gap.', question=question)
            reports[role] = output
            history.append({'round': round_index, 'role': role, 'kind': 'answer', **output})
        reflection = ask(examiner, f'ce_{round_index}_reflection', reports, history,
                         'Assess whether the answers resolved the question. Return the next targeted '
                         'interrogative question or null if resolved; do not repeat the target comment '
                         'or seek confirmation of agreement alone. Explain briefly in content.', schema=QUESTION_SCHEMA)
        history.append({'round': round_index, 'role': examiner, 'kind': 'reflection', **reflection})
        question = reflection['question']
        if early_stop and not question:
            return reports, history, 'information_saturation'
        if early_stop and previous is not None and stable(reports, previous, respondents, task):
            return reports, history, 'stagnation'
        previous = deepcopy(reports)
    return reports, history, 'max_rounds'
