from src.io_utils import digest
from src.courtroom_rl.env import CourtroomEnv
from src.courtroom_rl.schemas import Execution


def replay(case_input, trace, budget, sample_id=None):
    class RecordedExecutor:
        def __init__(self):
            self.index = 0

        def execute(self, state, action, target, budget):
            event = trace[env.state.decision_count]
            if event.get('budget_blocked'):
                from src.courtroom_rl.executor import BudgetExhausted
                exc = BudgetExhausted('Recorded request admission failure')
                exc.execution = Execution(**event['execution'])
                raise exc
            return Execution(**event['execution'])

    env = CourtroomEnv(RecordedExecutor(), budget)
    env.reset(case_input, sample_id=sample_id if sample_id is not None else trace[0]['sample_id'])
    for event in trace:
        if env.legal_actions() != event['legal_actions']:
            raise ValueError('Replay action masks differ')
        env.step(event['action'], event['target'])
        if digest(env.public_state()) != event['next_state_hash']:
            raise ValueError('Replay state differs')
    return env
