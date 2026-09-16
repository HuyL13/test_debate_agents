import time
from collections import defaultdict
from copy import deepcopy

from src.data.loader import ModelInput
from src.ars_diagnostic import execute as execute_ars
from src.ars_prompts import ars_system_prompt
from src.ars_schemas import ars_arbiter_schema, validate_ars_arbiter
from src.diagnostic import execute as execute_diagnostic
from src.io_utils import canonical
from src.labels import PROTOCOLS, ROLES, labels_for
from src.prompts import system_prompt
from src.legacy_protocols import EXECUTORS
from src.schemas import plan_schema, report_schema, review_schema, validate_plan, validate_review_quote
from src import simplified


class Engine:
    def __init__(self, llm, *, task, mode='adaptive', protocol='round_robin', max_rounds=3, early_stop=True,
                 adaptive_policy='planner', flow=None):
        labels_for(task)
        if mode not in ('single', 'no_deliberation', 'fixed', 'adaptive'):
            raise ValueError('Unknown engine mode')
        if protocol not in PROTOCOLS or type(max_rounds) is not int or not 1 <= max_rounds <= 5:
            raise ValueError('Protocol budget must be 1..5 with a registered protocol')
        self.llm, self.task, self.mode = llm, task, mode
        self.protocol, self.max_rounds, self.early_stop = protocol, max_rounds, early_stop
        if adaptive_policy not in ('planner', 'disagreement', 'diagnostic_no_debate', 'diagnostic_review',
                                   'ars_no_debate', 'ars_review'):
            raise ValueError('Unknown adaptive policy')
        self.adaptive_policy = adaptive_policy
        if flow not in (None, 'A', 'B'):
            raise ValueError('flow must be A or B')
        if flow and (mode not in ('no_deliberation', 'adaptive', 'fixed') or adaptive_policy != 'planner'):
            raise ValueError('Simplified flows require no_deliberation, fixed, or adaptive planner')
        self.flow = flow

    def run(self, model_input: ModelInput, metadata):
        if not isinstance(model_input, ModelInput):
            raise TypeError('Engine accepts only label-free ModelInput')
        started = time.monotonic()
        selected_protocol, plan = 'none', None
        decomposition = None
        if self.flow:
            model_input = ModelInput(model_input.title, model_input.parent_comment, model_input.comment)

        def ask(role, stage, reports, history, instruction, schema=None, question=None, validator=None, extra=None):
            payload = {'input': model_input.as_dict(), 'reports': deepcopy(reports),
                       'history': deepcopy(history), 'instruction': instruction, 'question': question,
                       'plan': deepcopy(plan), **deepcopy(extra or {})}
            if decomposition is not None:
                payload['decomposition'] = deepcopy(decomposition)

            ars_role = role in ('ARSArgumentDecomposer', 'Acceptability', 'Relevance', 'Sufficiency', 'ARSArbiter')
            if ars_role:
                selected_system_prompt = ars_system_prompt(role, self.task)
            elif self.flow:
                selected_system_prompt = simplified.prompt(role, self.task)
            else:
                selected_system_prompt = system_prompt(role, self.task)

            return self.llm.generate(system_prompt=selected_system_prompt, user_prompt=canonical(payload),
                                     schema=schema or (simplified.prediction_schema(self.task) if self.flow
                                                       else report_schema(self.task)),
                                     metadata={**metadata, 'task': self.task, 'role': role, 'stage': stage,
                                               'protocol': selected_protocol}, validator=validator)

        initial, final_agents, history = {}, {}, []
        if self.flow == 'B':
            decomposition = ask('ArgumentDecomposer', 'decomposition', {}, [],
                                'Extract explicit target premises and conclusion only.',
                                schema=simplified.decomposition_schema(),
                                validator=lambda value: simplified.validate_decomposition(value, model_input.comment))
        if self.mode == 'adaptive' and self.adaptive_policy in ('ars_no_debate', 'ars_review'):
            selected_protocol = self.adaptive_policy
            decomposition, initial, history, final_agents, reason = execute_ars(
                ask,
                model_input,
                self.adaptive_policy,
            )

            arbiter = ask(
                'ARSArbiter',
                'ars_final',
                {'final_diagnoses': final_agents},
                [],
                'Validate the final ARS diagnoses against the raw target and map them to exactly one final task prediction.',
                schema=ars_arbiter_schema(self.task),
                validator=lambda value: validate_ars_arbiter(value, self.task),
                extra={'decomposition': decomposition},
            )

            return {
                'framework': 'ARS',
                'prediction': arbiter['prediction'],
                'planner_protocol': selected_protocol,
                'plan': None,
                'decomposition': decomposition,
                'initial_diagnoses': initial,
                'diagnostic_review': history,
                'final_diagnoses': final_agents,
                'initial_agents': {},
                'deliberation': history,
                'final_agents': {},
                'arbiter': arbiter,
                'stop_reason': reason,
                'latency_seconds': time.monotonic() - started,
            }
        if self.mode == 'adaptive' and self.adaptive_policy in ('diagnostic_no_debate', 'diagnostic_review'):
            selected_protocol = self.adaptive_policy
            decomposition, initial, history, final_agents, reason, aggregation = execute_diagnostic(
                ask, model_input, self.adaptive_policy, self.task)
            if aggregation and aggregation['prediction'] == 'Non-Fallacious':
                arbiter = {'prediction': 'Non-Fallacious', 'confidence': 1.0,
                           'content': 'No supported closed-set CoCoLoFa candidate passed the detection hard gate.'}
            else:
                arbiter = ask('DiagnosticArbiter', 'final',
                              {'initial_diagnoses': initial, 'final_diagnoses': final_agents}, history,
                              'Synthesize decomposition and role-specific diagnoses. Produce exactly one final task prediction.',
                              extra={'decomposition': decomposition, 'detection_aggregation': aggregation})
            aggregation_trace = {k: v for k, v in (aggregation or {}).items() if k != 'prediction'}
            return {'prediction': arbiter['prediction'], 'planner_protocol': selected_protocol, 'plan': None,
                    'decomposition': decomposition, 'initial_diagnoses': initial,
                    'diagnostic_review': history, 'final_diagnoses': final_agents,
                    'initial_agents': {}, 'deliberation': history, 'final_agents': {},
                    'arbiter': arbiter, 'stop_reason': reason,
                    **aggregation_trace,
                    'latency_seconds': time.monotonic() - started}
        if self.mode == 'single':
            arbiter = ask('Single', 'single', {}, [], 'Predict the task label.')
            reason = 'single'
        else:
            # Independent prompts: reports from earlier calls never enter later initial calls.
            initial = {role: ask(role, 'initial', {}, [], 'Provide your independent role-specific assessment.')
                       for role in ROLES}
            final_agents = deepcopy(initial)
            reason = 'no_deliberation'
            if self.mode == 'adaptive' and self.adaptive_policy == 'disagreement':
                if len({report['prediction'] for report in initial.values()}) == 1:
                    reason = 'initial_consensus'
                else:
                    selected_protocol = 'independent_review'
                    plan = {'protocol': selected_protocol, 'order': list(ROLES), 'max_rounds': 1,
                            'reason': 'Initial labels disagree; one isolated review per role.'}
                    for role in ROLES:
                        output = ask(role, 'independent_review', initial, [],
                                     'Compare the competing initial predictions against the target text. '
                                     'Identify the strongest alternative interpretation and resolve the '
                                     'specific inference that distinguishes it. Keep or change your label '
                                     'based on that evidence, not confidence or vote counts. Include a '
                                     'nonempty verbatim supporting_quote from the target comment and '
                                     'explain its relevance in content. A quotation alone is not proof '
                                     'of a fallacy. Do not invent a disagreement when none is substantive.',
                                     schema=review_schema(self.task),
                                     validator=lambda value: validate_review_quote(value, model_input.comment))
                        final_agents[role] = output
                        history.append({'round': 0, 'role': role, 'kind': 'independent_review', **output})
                    reason = 'one_review_round'
            elif self.mode != 'no_deliberation':
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
        flow_trace = ({'flow': self.flow, 'agent_roles': simplified.ROLE_NAMES,
                       **({'decomposition': decomposition} if decomposition is not None else {})}
                      if self.flow else {})
        return {**flow_trace, 'prediction': arbiter['prediction'], 'planner_protocol': selected_protocol, 'plan': plan,
                'initial_agents': initial, 'deliberation': history, 'final_agents': final_agents,
                'arbiter': arbiter, 'stop_reason': reason, 'latency_seconds': time.monotonic() - started}
