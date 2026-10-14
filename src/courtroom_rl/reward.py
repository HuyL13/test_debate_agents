"""Private courtroom reward; CREW old/new component-gain pattern adapted.

Source: CREW rwg_env.py::get_q_torch/step, MIT (vendor/crew/LICENSE).
Paper-text similarity/EMA are incompatible here: bounded courtroom proxies and
a frozen source-only classifier replace them. Scores never enter public state.
"""
from dataclasses import asdict, dataclass
import math

import numpy as np

from src.io_utils import digest
from src.labels import FALLACIES
from src.courtroom_rl.schemas import ROLES


@dataclass(frozen=True)
class RewardConfig:
    mode: str = 'terminal'
    step_cost: float = .01
    token_cost: float = 1e-5
    call_cost: float = 0.
    invalid_cost: float = .1
    token_cost_basis: str = 'auto'
    progress_scale: float = .3
    local_weight: float = .4
    board_weight: float = .6
    weight_start: float = .2
    weight_end: float = .8
    local_scale: float = 1.
    board_scale: float = 1.
    decision_scale: float = 1.
    episode_progress_cap: float = .5
    suppress_wrong_charge_gain: bool = True
    alpha: float = .25
    gamma: float = .99
    log_floor: float = -6.
    epsilon: float = 1e-4
    horizon: int | None = None

    def __post_init__(self):
        if self.mode not in ('terminal','crew','potential'):
            raise ValueError('Unknown reward mode')
        if self.token_cost_basis not in ('auto','all','output'):
            raise ValueError('Unknown token cost basis')
        for k,v in asdict(self).items():
            if isinstance(v,float) and not math.isfinite(v):
                raise ValueError(f'Nonfinite reward setting: {k}')
        if min(self.step_cost,self.token_cost,self.call_cost,self.invalid_cost,self.progress_scale,self.alpha) < 0:
            raise ValueError('Reward costs/scales must be nonnegative')
        if min(self.local_scale,self.board_scale,self.decision_scale) <= 0:
            raise ValueError('Component normalization scales must be positive')
        if not 0 < self.episode_progress_cap < 1:
            raise ValueError('Episode progress cap must be below terminal payoff magnitude')
        if not 0 <= self.weight_start <= self.weight_end <= 1 or not 0 < self.gamma <= 1:
            raise ValueError('Invalid mixing weights or discount')
        if min(self.local_weight,self.board_weight) < 0 or not math.isclose(self.local_weight+self.board_weight,1.):
            raise ValueError('Local/board mixing weights must sum to one')
        if not self.log_floor < 0 or not 0 < self.epsilon < 1:
            raise ValueError('Invalid bounded log probability settings')
        if self.horizon is not None and (type(self.horizon) is not int or self.horizon < 1):
            raise ValueError('Reward horizon must be a positive integer')


def grounded_spans(payload,state):
    spans = payload.get('evidence_spans') or []
    if not spans and payload.get('supported_quote'):
        source = payload.get('source','comment')
        if source not in ('comment','parent_comment','title'):
            return []
        text = getattr(state.case_input,source)
        quote = payload['supported_quote']
        if not isinstance(quote,str) or not quote.strip() or quote not in text:
            return []
        start = text.index(quote)
        spans = [{'source':source,'start':start,'end':start+len(quote),'quote':quote}]
    valid = []
    for s in spans:
        if s.get('source') not in ('comment','parent_comment','title'):
            return []
        text = getattr(state.case_input,s['source'])
        start,end = s.get('start'),s.get('end')
        if type(start) is not int or type(end) is not int or not 0 <= start < end <= len(text) or text[start:end] != s.get('quote'):
            return []
        valid.append((s['source'],start,end,s['quote']))
    return sorted(set(valid))


def source_evidence_view(state):
    """Assessor input: source excerpts once, no rhetoric/labels/status/confidence."""
    spans = set()
    for c in state.claims:
        spans.update(grounded_spans({'evidence_spans':c.evidence_spans,
            'supported_quote':c.source_span['quote'],'source':c.source_span['source']},state))
    for event in state.argument_events:
        if not event.get('invalid') and not event.get('budget_blocked'):
            spans.update(grounded_spans(event.get('payload',{}),state))
    return {'input':state.case_input.as_dict(),'source_evidence':[list(s) for s in sorted(spans)]}


class RewardEngine:
    version = 'crew-component-delta-v1'

    def __init__(self,config,budget,assessor=None):
        self.config,self.budget,self.assessor = config,budget,assessor

    def reset(self,state,gold):
        self._gold = gold
        self.local_units = {r:set() for r in ROLES}
        self.progress_spent = 0.
        self._last_view = None
        self._last_probability = None
        self.enabled = gold is not None and self.config.mode != 'terminal'
        if self.enabled and self.assessor is None:
            raise ValueError('Dense reward requires a frozen assessor')
        self.scores = self._scores(state)
        self.potential = self._potential(state)

    def _gold_probability(self,state):
        key = digest(source_evidence_view(state))
        if key != self._last_view:
            values = np.asarray(self.assessor.probabilities(state),dtype=float)
            if values.shape != (8,) or not np.isfinite(values).all() or (values < 0).any() or not np.isclose(values.sum(),1.):
                raise ValueError('Assessor must return normalized finite eight-class probabilities')
            self._last_probability = float(values[FALLACIES.index(self._gold)])
            self._last_view = key
        return self._last_probability

    def _log_probability(self,state):
        return float(np.clip(math.log(max(self._gold_probability(state),self.config.epsilon)),self.config.log_floor,0.))

    def _potential(self,state):
        if not self.enabled or state.done:
            return 0.
        return self.config.alpha*self._log_probability(state)

    def _board(self,state):
        disputed = {event.get('target') for event in state.argument_events if event.get('action') == 'CHALLENGE'
                    and not event.get('invalid') and not event.get('budget_blocked') and grounded_spans(event.get('payload',{}),state)}
        units = {}
        for c in state.claims:
            spans = grounded_spans({'evidence_spans':c.evidence_spans,'supported_quote':c.source_span['quote'],
                                    'source':c.source_span['source']},state)
            if not spans:
                continue
            consistent = c.label == self._gold or (c.label != self._gold and c.status == 'DISPUTED' and c.claim_id in disputed)
            for span in spans:
                key = (c.label,span)
                units[key] = max(units.get(key,0.),float(consistent))
        return float(np.mean(list(units.values()))) if units else 0.

    def _scores(self,state):
        if not self.enabled:
            return {'local':{r:0. for r in ROLES},'board':0.,'decision':0.}
        return {'local':{r:min(1.,len(self.local_units[r])/self.budget.max_claims) for r in ROLES},
                'board':self._board(state),
                'decision':(self._log_probability(state)-self.config.log_floor)/(-self.config.log_floor)}

    def _update_local(self,state,event):
        if event.get('invalid') or event.get('budget_blocked'):
            return
        spans = grounded_spans(event.get('payload',{}),state)
        if not spans:
            return
        role,action = event['role'],event['action']
        label = event['payload'].get('label')
        kind = None
        if action in ('ACCUSE','REVISE_CHARGE','PROPOSE_ALTERNATIVE','DEFEND_CLAIM') and label == self._gold:
            kind = 'support'
        elif action == 'CHALLENGE':
            claim = next((c for c in state.claims if c.claim_id == event['target']),None)
            if claim and claim.label != self._gold:
                kind,label = 'reject',claim.label
        if kind:
            self.local_units[role].update((kind,label,span) for span in spans)

    def transition(self,state,event,input_tokens,output_tokens,calls):
        c = self.config
        before = self.scores
        potential_before = self.potential
        if self.enabled:
            self._update_local(state,event)
        after = self._scores(state)
        role = event['role']
        deltas = {'local':after['local'][role]-before['local'][role],
                  'board':after['board']-before['board'],'decision':after['decision']-before['decision']}
        normalized = {k:float(np.clip(v/getattr(c,k+'_scale'),-1,1)) for k,v in deltas.items()}
        horizon = c.horizon or self.budget.max_decisions
        t = max(0,state.decision_count-1)
        w = float(np.clip(c.weight_start+(c.weight_end-c.weight_start)*t/max(1,horizon-1),c.weight_start,c.weight_end))
        gated = False
        if self.enabled and c.mode == 'crew' and c.suppress_wrong_charge_gain and event['action'] in ('ACCUSE','REVISE_CHARGE','PROPOSE_ALTERNATIVE'):
            if event['target'] != self._gold and normalized['decision'] > 0:
                normalized['decision'] = 0.
                gated = True
        progress = (1-w)*(c.local_weight*normalized['local']+c.board_weight*normalized['board'])+w*normalized['decision']
        shaping = 0.
        self.potential = self._potential(state)
        if self.enabled and c.mode == 'crew':
            proposed = c.progress_scale*float(np.clip(progress,-1,1))
            remaining = max(0.,c.episode_progress_cap-self.progress_spent)
            shaping = float(np.clip(proposed,-remaining,remaining))
            self.progress_spent += abs(shaping)
        elif self.enabled and c.mode == 'potential':
            shaping = c.gamma*self.potential-potential_before
        basis = c.token_cost_basis
        if basis == 'auto':
            basis = 'output' if c.mode == 'crew' else 'all'
        tokens = output_tokens if basis == 'output' else input_tokens+output_tokens
        terminal = (1. if state.final_label == self._gold else -1.) if state.done and self._gold is not None else 0.
        rewards = {'terminal':terminal,'step_cost':-c.step_cost,'token_cost':-c.token_cost*tokens,
                   'call_cost':-c.call_cost*calls,'invalid':-c.invalid_cost*bool(event.get('invalid')),'shaping':shaping}
        diagnostics = {'mode':c.mode,'version':self.version,'enabled':self.enabled,'scores_before':before,'scores_after':after,
                       **{'delta_'+k:v for k,v in deltas.items()},'normalized_deltas':normalized,'w_t':w,
                       'progress':progress,'progress_spent':self.progress_spent,'wrong_charge_gain_suppressed':gated,
                       'potential_before':potential_before,'potential_after':self.potential,'token_cost_basis':basis}
        self.scores = after
        return rewards,diagnostics
