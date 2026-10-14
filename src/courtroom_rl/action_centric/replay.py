from src.io_utils import digest
from src.data.loader import ModelInput
from src.courtroom_rl.schemas import Execution
from src.courtroom_rl.executor import BudgetExhausted
from src.courtroom_rl.action_centric.env import CourtroomEnv, Budget


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
        if env.legal_actions()!=event['legal_actions']:raise ValueError('Replay action mask differs')
        env.step(event['action'])
        if digest(env.public_state())!=event['next_state_hash']:raise ValueError('Replay state differs')
    return env
