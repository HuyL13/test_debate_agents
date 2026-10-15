"""Replay recorded V4 executions, checking both factorized legal masks and state."""
import math
from src.io_utils import digest
from src.data.loader import ModelInput
from src.courtroom_rl.schemas import Execution
from src.courtroom_rl.executor import BudgetExhausted
from .env import CourtroomEnv, Budget


def replay(row):
    class Recorded:
        def initialize(self,state,budget):return Execution(**row['initialization']['execution'])
        def execute(self,state,action,budget):
            event=row['trace'][state.decision_count]
            result=Execution(**event['execution'])
            if event.get('budget_blocked'):
                exc=BudgetExhausted('Recorded admission failure');exc.execution=result;raise exc
            return result
    env=CourtroomEnv(Recorded(),Budget(**row['budget']))
    env.reset(ModelInput(**row['case_input']),sample_id=row['sample_id'])
    if env.initialization['next_state_hash']!=row['initialization']['next_state_hash']:
        raise ValueError('Initialization replay differs')
    for event in row['trace']:
        legal=env.legal_actions()
        if legal!=event['legal_actions']:raise ValueError('Replay action mask differs')
        masks={a:env.legal_targets(a) for a in legal}
        if masks!=event['legal_targets']:raise ValueError('Replay target mask differs')
        decision=event.get('decision',{})
        if 'legal' in decision and decision['legal']!=legal:raise ValueError('Replay policy action mask differs')
        if 'targets' in decision and decision['targets']!=masks:raise ValueError('Replay policy target mask differs')
        selected=event.get('actor_target',event.get('target'))
        if 'action' in decision and decision['action']!=event['action']:raise ValueError('Replay policy action differs')
        if 'target' in decision and decision['target']!=selected:raise ValueError('Replay policy target differs')
        keys=('logprob','action_logprob','target_logprob')
        if any(k in decision for k in keys):
            if not all(k in decision and math.isfinite(decision[k]) and decision[k]<=1e-6 for k in keys):
                raise ValueError('Replay policy logprob invalid')
            if not math.isclose(decision['logprob'],decision['action_logprob']+decision['target_logprob'],abs_tol=1e-5):
                raise ValueError('Replay policy joint logprob differs')
            if selected is None and abs(decision['target_logprob'])>1e-6:raise ValueError('Replay no-target logprob differs')
        env.step(event['action'],selected)
        if digest(env.public_state())!=event['next_state_hash']:raise ValueError('Replay state differs')
    return env
