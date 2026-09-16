import json

import pytest

from src.data.loader import ModelInput
from src.engine import Engine
from src.labels import ARS_ROLES
from src.llm.client import Client
from src.llm.config import ModelConfig
from src.schemas import validate_output


TARGET = (
    'Many people believe X, '
    'therefore X is true.'
)


class ARSTestLLM:
    def __init__(self):
        self.calls = []

    def generate(
        self,
        *,
        system_prompt,
        user_prompt,
        schema,
        metadata,
        validator=None,
    ):
        payload = json.loads(user_prompt)

        self.calls.append({
            'metadata': metadata.copy(),
            'payload': payload,
            'system_prompt': system_prompt,
            'schema': schema,
        })

        role = metadata['role']

        if role == 'ARSArgumentDecomposer':
            value = {
                'argumentative_status': 'explicit_argument',
                'claims': [
                    {
                        'id': 'C1',
                        'source': 'target_comment',
                        'role': 'premise',
                        'text': 'Many people believe X',
                        'qualifiers': [],
                        'modality': 'asserted',
                    },
                    {
                        'id': 'C2',
                        'source': 'target_comment',
                        'role': 'conclusion',
                        'text': 'X is true',
                        'qualifiers': [],
                        'modality': 'asserted',
                    },
                ],
                'main_conclusion_id': 'C2',
                'implicit_assumptions': [],
                'inference_links': [
                    {
                        'from': ['C1'],
                        'to': 'C2',
                        'relation': 'support',
                    }
                ],
                'scope_notes': [],
                'uncertainty': [],
            }

        elif role == 'Acceptability':
            value = {
                'decomposition_check': {
                    'status': 'accept',
                    'corrections': [],
                },
                'premise_ids': ['C1'],
                'dimension_status': 'satisfied',
                'acceptability_basis': 'speaker_commitment',
                'problematic_commitment': '',
                'finding': 'The popularity premise is explicitly asserted.',
                'supporting_quote': 'Many people believe X',
                'charitable_reading': 'Provisionally accept the popularity statement.',
            }

        elif role == 'Relevance':
            value = {
                'decomposition_check': {
                    'status': 'accept',
                    'corrections': [],
                },
                'premise_ids': ['C1'],
                'conclusion_id': 'C2',
                'dimension_status': 'violated',
                'relevance_gap': 'Popularity does not itself bear on truth.',
                'finding': 'The stated reason does not directly support truth.',
                'supporting_quote': 'Many people believe X',
                'charitable_reading': 'Popularity may show common acceptance.',
            }

        elif role == 'Sufficiency':
            value = {
                'decomposition_check': {
                    'status': 'accept',
                    'corrections': [],
                },
                'premise_ids': ['C1'],
                'conclusion_id': 'C2',
                'dimension_status': 'violated',
                'missing_warrant': 'If many people believe a claim, the claim is true.',
                'scope_or_strength_gap': 'Prevalence of belief is weaker than truth.',
                'finding': 'The premise is insufficient for the asserted conclusion.',
                'supporting_quote': 'therefore X is true',
                'charitable_reading': 'The speaker may mean X is widely accepted.',
            }

        elif role == 'ARSArbiter':
            value = {
                'validated_dimensions': {
                    'acceptability': 'supported',
                    'relevance': 'unsupported',
                    'sufficiency': 'unsupported',
                },
                'candidate_type': 'Appeal to Majority',
                'nearest_competitor': 'Hasty Generalization',
                'mapping_reason': (
                    'Popularity is used as justification for truth rather than '
                    'as a sample for population generalization.'
                ),
                'prediction': 'Fallacious',
                'content': 'The target instantiates a closed-set pattern.',
            }

        else:
            raise AssertionError(f'Unexpected role: {role}')

        if metadata['stage'] == 'ars_review':
            value = {
                'review_action': 'keep',
                'peer_effect': 'No peer report defeats this dimension finding.',
                **value,
            }

        validate_output(value, schema)

        if validator is not None:
            validator(value)

        return value


def test_ars_roles_are_distinct():
    assert ARS_ROLES == (
        'Acceptability',
        'Relevance',
        'Sufficiency',
    )


def test_ars_no_debate_has_five_calls():
    llm = ARSTestLLM()

    engine = Engine(
        llm,
        task='detection',
        mode='adaptive',
        adaptive_policy='ars_no_debate',
    )

    result = engine.run(
        ModelInput('', '', TARGET),
        {'sample_id': 'ars:test'},
    )

    roles = [
        call['metadata']['role']
        for call in llm.calls
    ]

    assert roles == [
        'ARSArgumentDecomposer',
        'Acceptability',
        'Relevance',
        'Sufficiency',
        'ARSArbiter',
    ]

    assert result['framework'] == 'ARS'


def test_only_ars_arbiter_sees_labels():
    llm = ARSTestLLM()

    engine = Engine(
        llm,
        task='detection',
        mode='adaptive',
        adaptive_policy='ars_no_debate',
    )

    engine.run(ModelInput('', '', TARGET), {})

    forbidden = (
        'Appeal to Authority',
        'Appeal to Majority',
        'Appeal to Nature',
        'Appeal to Tradition',
        'Appeal to Worse Problems',
        'False Dilemma',
        'Hasty Generalization',
        'Slippery Slope',
        'Fallacious',
        'Non-Fallacious',
    )

    for call in llm.calls:
        if call['metadata']['role'] == 'ARSArbiter':
            continue

        for term in forbidden:
            assert term not in call['system_prompt']


def test_ars_initial_agents_are_independent():
    llm = ARSTestLLM()

    engine = Engine(
        llm,
        task='detection',
        mode='adaptive',
        adaptive_policy='ars_no_debate',
    )

    engine.run(ModelInput('', '', TARGET), {})

    initial_calls = [
        call
        for call in llm.calls
        if call['metadata']['stage'] == 'ars_initial'
    ]

    assert len(initial_calls) == 3

    for call in initial_calls:
        assert call['payload']['reports'] == {}
        assert call['payload']['history'] == []


def test_ars_review_is_synchronous():
    llm = ARSTestLLM()

    engine = Engine(
        llm,
        task='detection',
        mode='adaptive',
        adaptive_policy='ars_review',
    )

    result = engine.run(ModelInput('', '', TARGET), {})

    review_calls = [
        call
        for call in llm.calls
        if call['metadata']['stage'] == 'ars_review'
    ]

    assert len(llm.calls) == 8
    assert len(review_calls) == 3

    for call in review_calls:
        assert call['payload']['reports'] == result['initial_diagnoses']
        assert call['payload']['history'] == []


def test_ars_arbiter_sees_final_only():
    llm = ARSTestLLM()

    engine = Engine(
        llm,
        task='detection',
        mode='adaptive',
        adaptive_policy='ars_review',
    )

    result = engine.run(ModelInput('', '', TARGET), {})

    arbiter_call = next(
        call
        for call in llm.calls
        if call['metadata']['role'] == 'ARSArbiter'
    )

    assert arbiter_call['payload']['reports'] == {
        'final_diagnoses': result['final_diagnoses'],
    }
    assert arbiter_call['payload']['history'] == []


def test_label_leakage_is_rejected():
    from src.ars_schemas import validate_label_agnostic

    with pytest.raises(ValueError):
        validate_label_agnostic({
            'finding': 'This is Appeal to Majority.',
            'supporting_quote': 'Many people believe X',
        })


def test_label_name_inside_quote_is_allowed():
    from src.ars_schemas import validate_label_agnostic

    validate_label_agnostic({
        'finding': 'The speaker explicitly names a concept.',
        'supporting_quote': 'This is a slippery slope',
    })


def test_decomposition_claim_must_be_verbatim():
    from src.ars_schemas import validate_ars_decomposition

    value = {
        'argumentative_status': 'explicit_argument',
        'claims': [
            {
                'id': 'C1',
                'source': 'target_comment',
                'role': 'premise',
                'text': 'invented paraphrase',
                'qualifiers': [],
                'modality': 'asserted',
            }
        ],
        'main_conclusion_id': None,
        'implicit_assumptions': [],
        'inference_links': [],
        'scope_notes': [],
        'uncertainty': [],
    }

    with pytest.raises(ValueError):
        validate_ars_decomposition(
            value,
            {
                'title': '',
                'parent_comment': '',
                'comment': TARGET,
            },
        )


def test_detection_candidate_none_requires_nonfallacious():
    from src.ars_schemas import validate_ars_arbiter

    value = {
        'validated_dimensions': {
            'acceptability': 'supported',
            'relevance': 'supported',
            'sufficiency': 'supported',
        },
        'candidate_type': 'None',
        'nearest_competitor': 'Appeal to Majority',
        'mapping_reason': 'No benchmark class is established.',
        'prediction': 'Fallacious',
        'content': 'x',
    }

    with pytest.raises(ValueError):
        validate_ars_arbiter(value, 'detection')


@pytest.mark.parametrize('task', ['detection', 'classification'])
@pytest.mark.parametrize('policy', ['ars_no_debate', 'ars_review'])
def test_ars_mock_transport_supports_both_tasks_and_policies(tmp_path, task, policy):
    client = Client(
        ModelConfig(name='offline-mock-v1', provider='mock'),
        tmp_path / 'responses.sqlite',
        tmp_path / 'raw_calls.jsonl',
    )

    result = Engine(
        client,
        task=task,
        mode='adaptive',
        adaptive_policy=policy,
    ).run(ModelInput('', '', TARGET), {})

    assert result['framework'] == 'ARS'
    if task == 'detection':
        assert result['prediction'] in ('Non-Fallacious', 'Fallacious')
    else:
        assert result['prediction'] == result['arbiter']['candidate_type']
    assert result['stop_reason'] == policy
