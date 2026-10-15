"""Sequential actor action/target environment with source-grounded LLM arguments."""
from copy import deepcopy
from dataclasses import asdict

from src.labels import FALLACIES
from src.io_utils import digest
from src.courtroom_rl.executor import BudgetExhausted
from src.courtroom_rl.schemas import Execution
from src.courtroom_rl.reward import RewardConfig
from src.courtroom_rl.action_centric.reward import RewardEngine
from src.courtroom_rl.action_centric.state import Budget, State, ROLE_ACTIONS
from src.courtroom_rl.action_centric import ledger


from src.courtroom_rl.action_centric.env import CourtroomEnv as V3CourtroomEnv


class CourtroomEnv(V3CourtroomEnv):
    architecture='action_centric_v4'

    def __init__(self,executor,budget=None,assessor=None,semantic_observation=False,text_encoder=None,**reward_options):
        if reward_options.get('mode','terminal') != 'terminal':raise ValueError('V4 requires terminal reward')
        reward_options['mode']='terminal'
        self.executor=executor;self.budget=budget or Budget()
        if self.budget.max_claims+self.budget.max_hypotheses>16:raise ValueError('V4 object capacity is 16')
        self.semantic_observation=semantic_observation
        self.text_encoder=text_encoder
        if reward_options.get('token_cost_basis','auto')=='auto':
            reward_options['token_cost_basis']='output'
        self.reward_config=RewardConfig(**reward_options)
        self.reward_engine=RewardEngine(self.reward_config,self.budget,assessor)

    def public_state(self):return asdict(self.state)

    def _progress(self):
        client=getattr(self.executor,'client',None)
        return getattr(getattr(client,'transport',None),'progress',None)

    def reset(self,case_input,gold=None,sample_id=''):
        if gold is not None and gold not in FALLACIES:raise ValueError('Unknown gold class')
        self.state=State(case_input,sample_id);self.trace=[];self._gold=gold
        self.pending_action='TOP3_INIT'
        execution=self.executor.initialize(self.state,self.budget)
        self.state=ledger.initialize(self.state,execution.payload,self.budget)
        self._usage(execution)
        self.initialization={'execution':asdict(execution),'next_state_hash':digest(self.public_state())}
        # Initialization is not an actor action and does not receive shaping.
        self.reward_engine.reset(self.state,gold)
        self._force_if_needed()
        self.pending_action=None
        if self._progress():
            self._progress().log('INIT','Top3: '+' | '.join(f'{h.id}={h.label}' for h in self.state.hypotheses))
        return self.public_state()

    def _usage(self,execution):
        s=self.state;s.calls+=execution.calls;s.input_tokens+=execution.input_tokens
        s.output_tokens+=execution.output_tokens;s.estimated_usage_calls+=execution.estimated_usage_calls

    def _force_if_needed(self):
        s,b=self.state,self.budget
        exhausted=(s.decision_count>=b.max_decisions-1 or s.calls>=b.max_calls-1 or
            s.input_tokens+s.output_tokens>=b.max_tokens-b.verdict_reserve_tokens)
        if not s.done and exhausted:
            s.forced_verdict=True;s.active_role='Judge';s.pending_request=None

    def _base_legal_actions(self):
        s,b=self.state,self.budget
        if s.done:return []
        if s.forced_verdict:return ['VERDICT']
        if s.active_role=='Judge':
            legal=['VERDICT']
            for role,action,work in [('Prosecutor','REQUEST_SUPPORT','SUPPORT'),('Defender','REQUEST_REBUTTAL','CHALLENGE')]:
                scope=[t for t in ledger.eligible(s,work) if [action,s.revision,t] not in s.exhausted_requests]
                if not s.role_status[role] and scope and len(s.claims)<b.max_claims:
                    legal.insert(0,action)
            return legal
        legal=['REST']
        if s.active_role=='Prosecutor':
            if len(s.claims)<b.max_claims:
                if ledger.eligible(s,'SUPPORT'):legal.insert(0,'SUPPORT')
                if ledger.eligible(s,'REVISE'):legal.insert(0,'REVISE')
        else:
            if ledger.eligible(s,'CONCEDE'):legal.insert(0,'CONCEDE')
            if len(s.claims)<b.max_claims:
                if ledger.eligible(s,'CHALLENGE'):legal.insert(0,'CHALLENGE')
                if len(s.hypotheses)<b.max_hypotheses and not s.action_stats.get('Defender.PROPOSE_ALTERNATIVE',{}).get('no_op'):
                    legal.insert(0,'PROPOSE_ALTERNATIVE')
        return legal

    def legal_targets(self,action):
        if action not in self._base_legal_actions():return []
        work={'REQUEST_SUPPORT':'SUPPORT','REQUEST_REBUTTAL':'CHALLENGE'}.get(action,action)
        targets=ledger.eligible(self.state,work) if work in ('SUPPORT','CHALLENGE','CONCEDE','REVISE') else [None]
        if action.startswith('REQUEST_'):
            targets=[t for t in targets if [action,self.state.revision,t] not in self.state.exhausted_requests]
        request=self.state.pending_request
        if request and action not in ('REST','VERDICT'):
            if action not in ('SUPPORT','CHALLENGE','CONCEDE'):return []
            targets=[t for t in targets if t in request['eligible_claim_ids']]
        return targets

    def legal_actions(self):
        return [a for a in self._base_legal_actions() if self.legal_targets(a)]

    def step(self,action,target=None):
        legal=self.legal_actions()
        if action not in legal:raise ValueError('Illegal action type')
        target_masks={a:self.legal_targets(a) for a in legal}
        if target not in target_masks[action]:raise ValueError('Illegal actor target')
        actor_target=target
        self.actor_target=target;self.state.actor_target=target
        self.pending_action=action
        s=self.state;role=s.active_role;before=self.public_state();execution=Execution()
        invalid=no_op=budget_blocked=False;target=actor_target;error=None
        if action not in ('REST','REQUEST_SUPPORT','REQUEST_REBUTTAL'):
            try:execution=self.executor.execute(s,action,self.budget)
            except BudgetExhausted as exc:
                if action=='VERDICT':raise
                execution=getattr(exc,'execution',Execution());budget_blocked=True
            if not budget_blocked:
                if action=='VERDICT':
                    payload=ledger.grounded(s,execution.payload,True)
                    if payload.get('label') not in FALLACIES:raise ValueError('Invalid final verdict label')
                    s.done=True;s.final_label=payload['label'];execution.payload=payload
                else:
                    target=execution.payload.get('claim_id') or execution.payload.get('hypothesis_id')
                    try:
                        if action in ('SUPPORT','CHALLENGE','CONCEDE','REVISE') and target!=actor_target:
                            raise ValueError('Executor substituted actor target')
                        if action=='CONCEDE' and not str(execution.payload.get('reason','')).strip():
                            raise ValueError('Concession requires rationale')
                        committed,target,no_op=ledger.apply(s,action,execution.payload,self.budget)
                        self.state=s=committed
                        if not no_op and action!='CONCEDE':
                            execution.payload=ledger.grounded(s,execution.payload,action in ('REVISE','PROPOSE_ALTERNATIVE'))
                            if action in ('SUPPORT','CHALLENGE'):
                                execution.payload['label']=next(c.label for c in s.claims if c.claim_id==target)
                    except ValueError as exc:
                        invalid=True;no_op=True;error=str(exc)
                        target=actor_target
                        if actor_target is not None and [action,actor_target] not in s.invalid_targets:
                            s.invalid_targets.append([action,actor_target])
        elif action=='REST':
            if s.pending_request is None:s.role_status[role]=True
        self._usage(execution);s.decision_count+=1
        if action.startswith('REQUEST_'):
            recipient='Prosecutor' if action=='REQUEST_SUPPORT' else 'Defender'
            scope=[actor_target]
            s.pending_request={'role':recipient,'eligible_claim_ids':scope}
            s.exhausted_requests.append([action,s.revision,actor_target]);s.active_role=recipient
        elif not s.done:s.active_role='Judge';s.pending_request=None
        if budget_blocked:s.forced_verdict=True;s.active_role='Judge';s.pending_request=None
        self._force_if_needed()
        event={'role':role,'action':action,'target':target,'payload':deepcopy(execution.payload),
            'invalid':invalid,'no_op':no_op,'budget_blocked':budget_blocked}
        event['actor_target']=actor_target
        s.argument_events.append(event);s.action_history.append([role,action,target])
        s.no_ops+=int(no_op);s.invalid_actions+=int(invalid)
        # Adapt only private reward events to existing component-delta engine.
        reward_event=deepcopy(event)
        reward_event['action']={'SUPPORT':'DEFEND_CLAIM','REVISE':'REVISE_CHARGE'}.get(action,action)
        if action in ('REVISE','PROPOSE_ALTERNATIVE'):reward_event['target']=execution.payload.get('label')
        # No-op/invalid output cannot contaminate source-only assessor or scores.
        if no_op:reward_event['payload']={};reward_event['invalid']=True
        rewards,diagnostics=self.reward_engine.transition(s,reward_event,execution.input_tokens,execution.output_tokens,execution.calls)
        if no_op and not invalid:rewards['invalid']=-self.reward_config.invalid_cost
        # Public history uses structural ledger change, never private reward.
        key=role+'.'+action;stats=s.action_stats.setdefault(key,{'n':0,'impact':.5,'tokens':0.,'no_op':False})
        impact=float(s.revision>before['revision'] and not invalid and not no_op)
        stats['n']+=1;stats['impact']=.8*stats['impact']+.2*impact
        stats['tokens']+=execution.input_tokens+execution.output_tokens;stats['no_op']=no_op
        trace={'architecture':self.architecture,'sample_id':s.sample_id,'global_step':s.decision_count,
            'role':role,'action':action,'target':target,'actor_target':actor_target,'legal_actions':legal,'legal_targets':target_masks,'payload':deepcopy(execution.payload),
            'execution':asdict(execution),'invalid':invalid,'no_op':no_op,'error':error,'budget_blocked':budget_blocked,
            'forced_verdict':s.forced_verdict,'terminated':s.done,'truncated':False,'rewards':rewards,
            'reward_diagnostics':diagnostics,'next_state_hash':digest(self.public_state()),
            'ledger_revision':s.revision,'stop_reason':'budget' if s.forced_verdict else 'verdict' if s.done else None}
        self.trace.append(trace)
        self.pending_action=None
        if self._progress() and execution.calls:
            chosen=next((c for c in s.claims if c.claim_id==target),None)
            label=execution.payload.get('label') or (chosen.label if chosen else None)
            if action=='VERDICT':
                self._progress().log('VERDICT',f'prediction={s.final_label} forced={s.forced_verdict}')
            else:
                self._progress().log('RESULT',f'{role}.{action} target={target}'+
                    (f' fallacy={label}' if label is not None else '')+
                    f' no_op={no_op} invalid={invalid}')
        return self.public_state(),sum(rewards.values()),s.done,False,trace
