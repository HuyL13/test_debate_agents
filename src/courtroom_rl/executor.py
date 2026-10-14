"""Action adapters around the existing client and original courtroom prompts."""
import json
from dataclasses import asdict
from contextlib import nullcontext

from src.io_utils import digest
from src.schemas import object_schema
from src.courtroom_rl.schemas import Execution
from src.courtroom_rl.ledger import target_label, validate_payload
from src.courtroom_rl.vendor.baseline.adversarial_prompts import adversarial_system_prompt
from src.courtroom_rl.evidence import passages_for, evidence_schema, resolve_references
from src.courtroom_rl.prompts import action_prompt


class BudgetExhausted(RuntimeError):
    budget_exhausted = True


class UsageAwareCache:
    """Expose accounting provenance from the existing cache; no second store."""
    def __init__(self, cache):
        self.cache = cache
        self.last_usage_estimated = False

    def get(self, key):
        value = self.cache.get(key)
        self.last_usage_estimated = bool(value and value.get('response',{}).get('_courtroom_usage_estimated'))
        return value

    def put(self, key, value):
        self.cache.put(key,value)


def wrap_accounting(client):
    if not isinstance(client.transport,AccountingTransport):
        client.transport = AccountingTransport(client.transport)
    if not isinstance(client.cache,UsageAwareCache):
        client.cache = UsageAwareCache(client.cache)


class AccountingTransport:
    """Measure every attempted request, including rejected output and retries.

    Cached output has zero physical calls, but executor charges its logical token
    usage to keep inference-budget comparisons meaningful.
    """
    def __init__(self, transport, input_estimator=None):
        self.transport = transport
        self.input_estimator = input_estimator
        self.minimum_output_tokens = 1
        self.calls = self.input_tokens = self.output_tokens = 0
        self.estimated_usage_calls = 0
        self.limits = None
        self.progress = None
        self.progress_context = 'LLM request'
        self.action_attempt = 0

    def complete(self, payload):
        payload = dict(payload)
        # UTF-8 bytes are a conservative input estimate for byte-level tokenizers;
        # reserve message framing overhead as well. Provider usage is authoritative.
        prompt_material = {'messages':payload['messages'],'response_format':payload.get('response_format',{})}
        estimate = (int(self.input_estimator(payload)) if self.input_estimator is not None else
                    len(json.dumps(prompt_material, ensure_ascii=False).encode('utf-8')) + 128)
        if estimate<1:raise ValueError('Input token estimate must be positive')
        self.last_input_estimate=estimate
        if self.limits:
            max_calls, max_tokens = self.limits
            remaining = max_tokens-self.input_tokens-self.output_tokens
            if self.calls >= max_calls or remaining-estimate < self.minimum_output_tokens:
                exc=BudgetExhausted(f'Remaining budget cannot admit this request: input_estimate={estimate}, '
                    f'remaining_tokens={remaining}, remaining_calls={max_calls-self.calls}, '
                    f'minimum_output={self.minimum_output_tokens}')
                exc.input_estimate=estimate
                raise exc
            payload['max_completion_tokens'] = min(payload['max_completion_tokens'], remaining-estimate)
            if self.progress and self.input_estimator is not None:
                self.progress.log('BUDGET',f'{self.progress_context}: input_estimate={estimate} '
                    f'output_cap={payload["max_completion_tokens"]} remaining_tokens={remaining} remaining_calls={max_calls-self.calls}')
        self.calls += 1
        self.action_attempt += 1
        try:
            with self.progress.request(self.progress_context,self.action_attempt) if self.progress else nullcontext():
                response = self.transport.complete(payload)
        except Exception:
            # An accepted request may still consume provider tokens after a
            # client timeout. Reserve its full allowance instead of treating
            # unknown usage as free; reports mark these figures as estimates.
            self.input_tokens += estimate
            self.output_tokens += payload['max_completion_tokens']
            self.estimated_usage_calls += 1
            raise
        usage = response.get('usage') or {}
        inp, out = usage.get('prompt_tokens'), usage.get('completion_tokens')
        estimated = not (type(inp) is int and inp >= 0 and type(out) is int and out >= 0)
        if estimated:
            self.estimated_usage_calls += 1
        inp = inp if type(inp) is int and inp >= 0 else estimate
        out = out if type(out) is int and out >= 0 else payload['max_completion_tokens']
        self.input_tokens += inp
        self.output_tokens += out
        if self.limits and self.input_tokens+self.output_tokens>self.limits[1]:
            exc=BudgetExhausted('Provider reported usage exceeds remaining budget')
            exc.usage={'prompt_tokens':inp,'completion_tokens':out,'total_tokens':inp+out}
            raise exc
        if estimated:
            response = dict(response)
            response['_courtroom_provider_usage'] = usage
            response['_courtroom_usage_estimated'] = True
            response['usage'] = {'prompt_tokens':inp,'completion_tokens':out,'total_tokens':inp+out}
        if self.input_estimator is not None:
            response=dict(response)
            response['_courtroom_budget']={'input_estimate':estimate,'actual_prompt_tokens':inp,
                'usage_estimated':estimated,'estimator':getattr(self.input_estimator,'name','custom')}
        return response


class LLMExecutor:
    prompt_version = 'courtroom-single-action-v3'

    def __init__(self, client):
        self.client = client
        wrap_accounting(client)
        self._prepared = None
        self._prepared_failure = None

    def prepare_initial(self, state, budget):
        """Frozen heuristic chooses label; its output is executed once, not twice.

        This step is for non-PPO baselines only. Learned rollouts sample their
        own ACCUSE label and never borrow a heuristic action log probability.
        """
        from src.courtroom_rl.vendor.baseline.adversarial_schemas import prosecutor_schema, validate_prosecutor
        passages = passages_for(state.case_input,target_only=True)
        schema = prosecutor_schema('classification')
        del schema['properties']['quote']
        schema['properties']['evidence_ids'] = evidence_schema(passages)
        schema['required'] = ['evidence_ids' if k == 'quote' else k for k in schema['required']]
        transport = self.client.transport
        transport.progress_context = 'Prosecutor.ACCUSE target=auto'
        transport.action_attempt = 0
        start = transport.calls, transport.input_tokens, transport.output_tokens, transport.estimated_usage_calls
        transport.limits = (transport.calls+budget.max_calls-state.calls,
                            transport.input_tokens+transport.output_tokens+budget.max_tokens-state.input_tokens-state.output_tokens)

        def validator(value):
            grounded = resolve_references(value,passages)
            validate_prosecutor({**value,'quote':grounded['supported_quote']}, state.case_input.comment, 'classification')

        try:
            result = self.client.generate(system_prompt=adversarial_system_prompt('Prosecutor', 'classification')+
                '\nEVIDENCE FORMAT OVERRIDE: Select evidence_ids from supplied passages; do not generate quote text or offsets. Return the supplied schema.',
                user_prompt=json.dumps({'input':state.case_input.as_dict(),'evidence_passages':passages,
                    'instruction':'Select the best-fitting class and supporting passage IDs, with a defect mechanism.'}),
                schema=schema, validator=validator,
                metadata={'sample_id':state.sample_id,'stage':'heuristic_initial_charge','prompt_version':self.prompt_version})
            if result.stats.cache_hit and (budget.max_calls-state.calls < 1 or
                    result.stats.total_tokens > budget.max_tokens-state.input_tokens-state.output_tokens):
                raise BudgetExhausted('Cached initial charge exceeds remaining logical budget')
        except BudgetExhausted as exc:
            exc.execution = Execution(calls=transport.calls-start[0], input_tokens=transport.input_tokens-start[1],
                                      output_tokens=transport.output_tokens-start[2],estimated_usage_calls=transport.estimated_usage_calls-start[3])
            self._prepared_failure = exc
            raise
        obj = resolve_references(result.output,passages)
        payload = {'label':obj['candidate_class'],'supported_quote':obj['supported_quote'],'source':obj['source'],
                   'evidence_ids':obj['evidence_ids'],'evidence_spans':obj['evidence_spans'],
                   'mechanism':obj['defect_mechanism'],'attacks_claim_ids':[],'answer_to_pending_request':''}
        stats = result.stats
        execution = Execution(payload,
            1 if stats.cache_hit else transport.calls-start[0],
            stats.prompt_tokens if stats.cache_hit else transport.input_tokens-start[1],
            stats.completion_tokens if stats.cache_hit else transport.output_tokens-start[2], digest(payload),
            int(self.client.cache.last_usage_estimated) if stats.cache_hit else transport.estimated_usage_calls-start[3])
        self._prepared = (digest(asdict(state)), execution)
        return payload['label']

    def execute(self, state, action, target, budget):
        if self._prepared_failure is not None:
            exc, self._prepared_failure = self._prepared_failure, None
            raise exc
        if self._prepared is not None:
            state_hash, execution = self._prepared
            self._prepared = None
            if action != 'ACCUSE' or execution.payload['label'] != target or digest(asdict(state)) != state_hash:
                raise ValueError('Prepared initial accusation differs from selected action/state')
            return execution
        label = target_label(state, action, target)
        pending = state.pending_request[1] if state.pending_request else ''
        attacks = [target] if action == 'CHALLENGE' else []
        passages = passages_for(state.case_input,target_only=action in ('ACCUSE','REVISE_CHARGE'))
        schema = object_schema({
            'label': {'type': 'string', 'enum': [label]},
            'evidence_ids': evidence_schema(passages),
            'mechanism': {'type': 'string', 'minLength': 1},
            'attacks_claim_ids': {'type': 'array', 'items': {'type': 'string', 'enum': [c.claim_id for c in state.claims] or ['']}},
            'answer_to_pending_request': {'type': 'string', 'enum': [pending]},
        })
        prompt = action_prompt(state.active_role,action)
        example = {'label':label,'evidence_ids':[passages[0]['id']],
                   'mechanism':'Replace with the source-grounded explanation.',
                   'attacks_claim_ids':attacks,'answer_to_pending_request':pending}
        public = asdict(state)
        transport = self.client.transport
        transport.progress_context = f'{state.active_role}.{action} target={target}'
        transport.action_attempt = 0
        start = transport.calls, transport.input_tokens, transport.output_tokens, transport.estimated_usage_calls
        transport.limits = (transport.calls+budget.max_calls-state.calls,
                            transport.input_tokens+transport.output_tokens+budget.max_tokens-state.input_tokens-state.output_tokens)
        try:
            result = self.client.generate(
                system_prompt=prompt,
                user_prompt=json.dumps({'state': public, 'action': action, 'target': target,
                                        'selected_label': label, 'required_attacks': attacks,
                                        'evidence_passages':passages,'output_schema':schema,
                                        'output_example':example}, ensure_ascii=False),
                schema=schema,
                metadata={'sample_id': state.sample_id, 'stage': 'courtroom_action',
                          'prompt_version': self.prompt_version, 'state_hash': digest(public),
                          'action': action, 'target': target},
                validator=lambda value: validate_payload(resolve_references(value,passages), state, action, target),
            )
            if result.stats.cache_hit and (budget.max_calls-state.calls < 1 or
                    result.stats.total_tokens > budget.max_tokens-state.input_tokens-state.output_tokens):
                raise BudgetExhausted('Cached action exceeds remaining logical budget')
        except BudgetExhausted as exc:
            exc.execution = Execution(calls=transport.calls-start[0], input_tokens=transport.input_tokens-start[1],
                                      output_tokens=transport.output_tokens-start[2],estimated_usage_calls=transport.estimated_usage_calls-start[3])
            raise
        calls = transport.calls-start[0]
        inp, out = transport.input_tokens-start[1], transport.output_tokens-start[2]
        if result.stats.cache_hit:
            inp, out = result.stats.prompt_tokens, result.stats.completion_tokens
            calls = 1  # logical inference cost even if physically cached
        payload = resolve_references(result.output,passages)
        return Execution(payload, calls, inp, out, digest(payload),
                         int(self.client.cache.last_usage_estimated) if result.stats.cache_hit else transport.estimated_usage_calls-start[3])


class FixtureExecutor:
    """Deterministic plumbing fixture. Never a model or benchmark result."""
    def execute(self, state, action, target, budget):
        label = target_label(state, action, target)
        payload = {'label': label, 'supported_quote': state.case_input.comment[:120],
                   'source': 'comment', 'mechanism': f'Fixture {action} reasoning for {label}.',
                   'attacks_claim_ids': [target] if action == 'CHALLENGE' else [],
                   'answer_to_pending_request': state.pending_request[1] if state.pending_request else ''}
        return Execution(payload, 1, 25, 25, digest(payload))
