from dataclasses import asdict
from copy import deepcopy

from src.labels import FALLACIES
from src.io_utils import digest
from src.courtroom_rl.schemas import Budget, CourtState, Execution, TEXT_ACTIONS
from src.courtroom_rl.ledger import insert_claim, target_label, validate_payload
from src.courtroom_rl.reward import RewardConfig, RewardEngine


class CourtroomEnv:
    labels = FALLACIES

    def __init__(self, executor, budget=None, step_cost=.01, token_cost=1e-5, call_cost=0., invalid_cost=.1,assessor=None,**reward_options):
        self.executor = executor
        self.budget = budget or Budget()
        if min(step_cost, token_cost, call_cost, invalid_cost) < 0:
            raise ValueError('Costs cannot be negative')
        self.costs = step_cost, token_cost, call_cost, invalid_cost
        self.reward_config = RewardConfig(step_cost=step_cost,token_cost=token_cost,call_cost=call_cost,invalid_cost=invalid_cost,**reward_options)
        self.reward_engine = RewardEngine(self.reward_config,self.budget,assessor)

    def reset(self, case_input, gold=None, sample_id=''):
        if gold is not None and gold not in FALLACIES:
            raise ValueError('Gold outside eight-class taxonomy')
        self._gold = gold
        self.state = CourtState(case_input, sample_id)
        self.trace = []
        self.reward_engine.reset(self.state,gold)
        return self.public_state()

    def public_state(self):
        return asdict(self.state)

    def legal_actions(self):
        s, b = self.state, self.budget
        if s.done:
            return {}
        if s.forced_verdict:
            return {'VERDICT': list(FALLACIES)}
        if s.phase == 'INITIAL_CHARGE':
            return {'ACCUSE': list(FALLACIES)}
        legal = {}
        available = [c for c in s.claims if c.status not in ('CONCEDED', 'CLOSED')]
        if s.active_role == 'Prosecutor':
            legal['REST_CASE'] = [None]
            requested = s.pending_request[1] if s.pending_request else None
            targets = [c.claim_id for c in available if c.claim_id == requested and c.response_count == 0]
            if targets:
                legal['DEFEND_CLAIM'] = targets
            if not s.revised and len(s.claims) < b.max_claims:
                labels = [x for x in FALLACIES if x not in s.tested_labels or
                          (x in s.candidate_labels and x != s.charge_label)]
                if labels:
                    legal['REVISE_CHARGE'] = labels
        elif s.active_role == 'Defender':
            legal['REST_DEFENSE'] = [None]
            requested = s.pending_request[1] if s.pending_request else None
            eligible = [c for c in available if requested is None or c.claim_id == requested]
            challenges = [c.claim_id for c in eligible if c.challenge_count == 0]
            if challenges:
                legal['CHALLENGE'] = challenges
            concessions = [c.claim_id for c in eligible if c.author != 'Defender']
            if concessions:
                legal['CONCEDE'] = concessions
            if not s.alternative_proposed and len(s.claims) < b.max_claims:
                labels = [x for x in FALLACIES if x not in s.tested_labels]
                if labels:
                    legal['PROPOSE_ALTERNATIVE'] = labels
        else:
            if s.defense_exposed:
                legal['VERDICT'] = list(FALLACIES)
            for role, action in [('Prosecutor', 'REQUEST_PROSECUTOR'), ('Defender', 'REQUEST_DEFENDER')]:
                if s.role_status[role]:
                    continue
                targets = []
                for c in available:
                    if [role, c.claim_id] in s.exhausted_requests:
                        continue
                    if role == 'Prosecutor' and c.response_count == 0 and (c.status == 'DISPUTED' or c.author == 'Defender'):
                        targets.append(c.claim_id)
                    elif role == 'Defender' and c.author == 'Prosecutor' and c.challenge_count == 0:
                        targets.append(c.claim_id)
                if targets:
                    legal[action] = targets
        return legal

    def step(self, action, target):
        legal = self.legal_actions()
        if action not in legal or target not in legal[action]:
            raise ValueError(f'Illegal action/target: {action}/{target}')
        s = self.state
        before = self.public_state()
        role, phase = s.active_role, s.phase
        result = Execution()
        invalid = False
        budget_blocked = False
        if action in TEXT_ACTIONS:
            # Failed API/schema attempts raise; runner marks infrastructure failure.
            # No fabricated prediction or corrupted rollout is silently accepted.
            from src.courtroom_rl.executor import BudgetExhausted
            try:
                result = self.executor.execute(s, action, target, self.budget)
                validate_payload(result.payload, s, action, target)
            except BudgetExhausted as exc:
                result = getattr(exc, 'execution', Execution())
                budget_blocked = True
        if budget_blocked:
            pass
        elif action in ('ACCUSE', 'REVISE_CHARGE', 'PROPOSE_ALTERNATIVE'):
            try:
                insert_claim(s, action, result.payload)
            except ValueError as exc:
                if 'Duplicate' not in str(exc):
                    raise
                invalid = True
            if not invalid:
                if target not in s.tested_labels:
                    s.tested_labels.append(target)
                if action == 'PROPOSE_ALTERNATIVE':
                    s.candidate_labels.append(target)
                    s.alternative_proposed = True
                else:
                    s.charge_label = target
                    s.revised |= action == 'REVISE_CHARGE'
        elif action in ('CHALLENGE', 'CONCEDE', 'DEFEND_CLAIM'):
            claim = next(c for c in s.claims if c.claim_id == target)
            if action == 'CHALLENGE':
                claim.status = 'DISPUTED'
                claim.challenge_count += 1
            elif action == 'CONCEDE':
                claim.status = 'CONCEDED'
            else:
                claim.status = 'RESPONDED'
                claim.response_count += 1
        elif action.startswith('REST_'):
            s.role_status[role] = True
        elif action == 'VERDICT':
            s.done = True
            s.final_label = target
            s.phase = 'TERMINAL'

        s.calls += result.calls
        s.input_tokens += result.input_tokens
        s.output_tokens += result.output_tokens
        s.estimated_usage_calls += result.estimated_usage_calls
        s.decision_count += 1
        s.action_history.append([role, action, target, digest(result.payload)])
        if role == 'Defender':
            s.defense_exposed = True
        if action.startswith('REQUEST_'):
            requested_role = 'Prosecutor' if action == 'REQUEST_PROSECUTOR' else 'Defender'
            s.pending_request = (requested_role, target)
            s.exhausted_requests.append([requested_role, target])
            s.active_role, s.phase = requested_role, 'FOLLOWUP'
        elif not s.done:
            s.pending_request = None
            s.active_role = 'Defender' if action == 'ACCUSE' else 'Judge'
            s.phase = 'DEFENSE_REVIEW' if action == 'ACCUSE' else 'JUDGE_REVIEW'
        exhausted = (budget_blocked or s.decision_count >= self.budget.max_decisions or s.calls >= self.budget.max_calls or
                     s.input_tokens+s.output_tokens >= self.budget.max_tokens)
        if not s.done and exhausted:
            # A separate on-policy Judge transition resolves the cap. This is
            # terminal classification, never an unscored time-limit truncation.
            s.forced_verdict = True
            s.pending_request = None
            s.active_role, s.phase = 'Judge', 'JUDGE_REVIEW'
        event = {'role': role, 'action': action, 'target': target, 'phase': phase,
                 'payload': deepcopy(result.payload), 'invalid': invalid, 'budget_blocked': budget_blocked}
        s.argument_events.append(event)
        if not invalid and not budget_blocked:
            for evidence_id in result.payload.get('evidence_ids',[]):
                if evidence_id not in s.seen_evidence_ids:
                    s.seen_evidence_ids.append(evidence_id)
        rewards,diagnostics = self.reward_engine.transition(s,event,result.input_tokens,result.output_tokens,result.calls)
        after = self.public_state()
        record = {'global_step': len(self.trace), 'sample_id': s.sample_id, **event,
                  'legal_actions': deepcopy(legal), 'rewards': rewards,'reward_diagnostics':diagnostics,
                  'execution': asdict(result), 'terminated': s.done, 'truncated': False,
                  'forced_verdict': s.forced_verdict,
                  'stop_reason': ('budget' if s.forced_verdict else 'judge_verdict') if s.done else None,
                  'changed_fields': [k for k in before if before[k] != after[k]],
                  'next_state_hash': digest(after)}
        self.trace.append(record)
        return after, sum(rewards.values()), s.done, False, record
