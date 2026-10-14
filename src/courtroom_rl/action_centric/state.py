from dataclasses import dataclass, field
from src.courtroom_rl.schemas import Claim as LegacyClaim
from src.data.loader import ModelInput

ROLE_ACTIONS = {'Prosecutor':('SUPPORT','REVISE','REST'),
                'Defender':('CHALLENGE','PROPOSE_ALTERNATIVE','CONCEDE','REST'),
                'Judge':('REQUEST_SUPPORT','REQUEST_REBUTTAL','VERDICT')}


@dataclass(frozen=True)
class Budget:
    max_decisions: int = 10
    max_calls: int = 8
    max_tokens: int = 24000
    max_claims: int = 8
    max_hypotheses: int = 8
    max_initial_claims_per_hypothesis: int = 1
    verdict_reserve_tokens: int = 8000

    def __post_init__(self):
        if any(type(v) is not int or v<1 for v in vars(self).values()):
            raise ValueError('Budget settings must be positive integers')
        if not 1<=self.max_decisions<=10 or self.max_calls<2 or self.max_claims<3 or not 3<=self.max_hypotheses<=8:
            raise ValueError('V3 requires <=10 decisions, >=2 calls and capacity for Top3')
        if self.verdict_reserve_tokens>=self.max_tokens:
            raise ValueError('Verdict reserve must be smaller than total token budget')
        if self.max_initial_claims_per_hypothesis not in (1,2):
            raise ValueError('Initialization supports one or two claims per hypothesis')


@dataclass
class Hypothesis:
    id: str
    label: str
    initial_rank: int | None
    claim_ids: list = field(default_factory=list)
    status: str = 'ACTIVE'
    visits: int = 0


@dataclass
class Claim(LegacyClaim):
    hypothesis_id: str = ''
    kind: str = 'SUPPORTING'


@dataclass
class State:
    case_input: ModelInput
    sample_id: str = ''
    hypotheses: list = field(default_factory=list)
    claims: list = field(default_factory=list)
    argument_events: list = field(default_factory=list)
    seen_evidence_ids: list = field(default_factory=list)
    active_role: str = 'Prosecutor'
    pending_request: dict | None = None
    decision_count: int = 0
    calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    estimated_usage_calls: int = 0
    done: bool = False
    final_label: str | None = None
    forced_verdict: bool = False
    role_status: dict = field(default_factory=lambda:{'Prosecutor':False,'Defender':False})
    action_history: list = field(default_factory=list)
    action_stats: dict = field(default_factory=dict)
    exhausted_requests: list = field(default_factory=list)
    attempted_units: list = field(default_factory=list)
    invalid_targets: list = field(default_factory=list)
    revision: int = 0
    init_labels: list = field(default_factory=list)
    no_ops: int = 0
    invalid_actions: int = 0
