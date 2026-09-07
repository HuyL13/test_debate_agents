import time
from collections import defaultdict
from copy import deepcopy

from src.data.loader import ModelInput
from src.io_utils import canonical
from src.labels import PROTOCOLS, ROLES, labels_for
from src.prompts import system_prompt
from src.protocols import EXECUTORS
from src.schemas import plan_schema, report_schema, validate_plan


class Engine:
    def __init__(self, llm, *, task, mode='adaptive', protocol='round_robin', max_rounds=3, early_stop=True):
        labels_for(task)
        if mode not in ('single', 'no_deliberation', 'fixed', 'adaptive'):
            raise ValueError('Unknown engine mode')
        if protocol not in PROTOCOLS or type(max_rounds) is not int or not 1 <= max_rounds <= 5:
            raise ValueError('Protocol budget must be 1..5 with a registered protocol')
        self.llm, self.task, self.mode = llm, task, mode
        self.protocol, self.max_rounds, self.early_stop = protocol, max_rounds, early_stop

    def run(self, model_input: ModelInput, metadata):
        if not isinstance(model_input, ModelInput):
            raise TypeError('Engine accepts only label-free ModelInput')
        started = time.monotonic()
        selected_protocol, plan = 'none', None

        def ask(role, stage, reports, history, instruction, schema=None, question=None, validator=None):
            payload = {'input': model_input.as_dict(), 'reports': deepcopy(reports),
                       'history': deepcopy(history), 'instruction': instruction, 'question': question,
                       'plan': deepcopy(plan)}
            return self.llm.generate(system_prompt=system_prompt(role, self.task), user_prompt=canonical(payload),
                                     schema=schema or report_schema(self.task),
                                     metadata={**metadata, 'task': self.task, 'role': role, 'stage': stage,
                                               'protocol': selected_protocol}, validator=validator)

        initial, final_agents, history = {}, {}, []
        if self.mode == 'single':
            arbiter = ask('Single', 'single', {}, [], 'Predict the task label.')
            reason = 'single'
        else:
            # Independent prompts: reports from earlier calls never enter later initial calls.
            initial = {role: ask(role, 'initial', {}, [], 'Provide your independent role-specific assessment.')
                       for role in ROLES}
            final_agents = deepcopy(initial)
            reason = 'no_deliberation'
            if self.mode != 'no_deliberation':
                if self.mode == 'adaptive':
                    plan = ask('Planner', 'plan', initial, [],
                               f'Select the protocol and execution parameters. Maximum budget: {self.max_rounds}.',
                               schema=plan_schema(self.max_rounds, initial),
                               validator=lambda p: validate_plan(p, self.max_rounds, initial))
                else:
                    groups = defaultdict(list)
                    for role in ROLES:
                        groups[initial[role]['prediction']].append(role)
                    affirmative = next(iter(groups.values())) if len(groups) == 2 else ['Factual']
                    plan = {'protocol': self.protocol, 'topic': 'Resolve differences in the target assessment.',
                            'reason': 'Fixed-protocol ablation; deterministic role assignment.',
                            'order': list(ROLES), 'affirmative': affirmative,
                            'negative': [r for r in ROLES if r not in affirmative],
                            'examiner': 'Factual', 'max_rounds': self.max_rounds}
                validate_plan(plan, self.max_rounds)
                selected_protocol = plan['protocol']
                final_agents, history, reason = EXECUTORS[selected_protocol](
                    ask, initial, plan, self.task, self.early_stop)
            arbiter = ask('Arbiter', 'final', {'initial': initial, 'final': final_agents}, history,
                          'Synthesize the evidence and produce exactly one final task prediction.')
        return {'prediction': arbiter['prediction'], 'planner_protocol': selected_protocol, 'plan': plan,
                'initial_agents': initial, 'deliberation': history, 'final_agents': final_agents,
                'arbiter': arbiter, 'stop_reason': reason, 'latency_seconds': time.monotonic() - started}
