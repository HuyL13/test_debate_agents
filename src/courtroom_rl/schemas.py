from dataclasses import asdict, dataclass, field

from src.data.loader import ModelInput


ROLES = ('Prosecutor', 'Defender', 'Judge')
ACTIONS = ('ACCUSE', 'DEFEND_CLAIM', 'REVISE_CHARGE', 'REST_CASE',
           'CHALLENGE', 'PROPOSE_ALTERNATIVE', 'CONCEDE', 'REST_DEFENSE',
           'REQUEST_PROSECUTOR', 'REQUEST_DEFENDER', 'VERDICT')


@dataclass(frozen=True)
class Budget:
    max_decisions: int = 8
    max_calls: int = 8
    max_tokens: int = 24000
    max_claims: int = 3

    def __post_init__(self):
        if any(type(v) is not int or v < 1 for v in asdict(self).values()):
            raise ValueError('Budget caps must be positive integers')
        if self.max_claims > 3:
            raise ValueError('V1 supports at most three claims')


@dataclass
class Claim:
    claim_id: str
    author: str
    label: str
    proposition: str
    source_span: dict
    supporting_ids: list = field(default_factory=list)
    attacks_ids: list = field(default_factory=list)
    status: str = 'OPEN'
    challenge_count: int = 0
    response_count: int = 0
    normalized_fingerprint: str = ''
    created_step: int = 0
    relation: str = 'accusation'
    similarity_review_candidates: list = field(default_factory=list)
    evidence_spans: list = field(default_factory=list)


@dataclass
class CourtState:
    case_input: ModelInput
    sample_id: str
    active_role: str = 'Prosecutor'
    phase: str = 'INITIAL_CHARGE'
    charge_label: str | None = None
    candidate_labels: list = field(default_factory=list)
    claims: list = field(default_factory=list)
    argument_events: list = field(default_factory=list)
    pending_request: tuple | None = None
    role_status: dict = field(default_factory=lambda: {'Prosecutor': False, 'Defender': False})
    action_history: list = field(default_factory=list)
    exhausted_requests: list = field(default_factory=list)
    tested_labels: list = field(default_factory=list)
    seen_evidence_ids: list = field(default_factory=list)
    decision_count: int = 0
    calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    estimated_usage_calls: int = 0
    defense_exposed: bool = False
    revised: bool = False
    alternative_proposed: bool = False
    done: bool = False
    forced_verdict: bool = False
    final_label: str | None = None


@dataclass
class Execution:
    payload: dict = field(default_factory=dict)
    calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    output_hash: str = ''
    estimated_usage_calls: int = 0


TEXT_ACTIONS = {'ACCUSE', 'CHALLENGE', 'DEFEND_CLAIM', 'REVISE_CHARGE', 'PROPOSE_ALTERNATIVE'}
