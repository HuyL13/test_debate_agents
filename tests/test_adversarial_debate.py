"""Unit tests for Adversarial Dialectical Debate (Prosecutor vs. Defender)."""

import pytest

from src.adversarial_prompts import adversarial_system_prompt
from src.adversarial_schemas import (
    prosecutor_schema,
    defender_schema,
    dialectical_arbiter_schema,
    validate_prosecutor,
    validate_defender,
    validate_dialectical_arbiter,
)
from src.adversarial_debate import execute as execute_adversarial
from src.engine import Engine
from src.data.loader import ModelInput
from src.labels import FALLACIES


class MockScriptedLLM:
    def __init__(self, responses):
        self.responses = list(responses)
        self.call_history = []

    def generate(self, system_prompt, user_prompt, schema=None, metadata=None, validator=None):
        self.call_history.append({'system_prompt': system_prompt, 'metadata': metadata})
        resp = self.responses.pop(0)
        if validator:
            validator(resp)
        return resp


def test_adversarial_prompts():
    p_pros = adversarial_system_prompt('Prosecutor', 'detection', use_patterns=True)
    assert "PROSECUTOR" in p_pros
    assert "Slippery Slope" in p_pros

    p_def = adversarial_system_prompt('Defender', 'detection')
    assert "DEFENDER" in p_def
    assert "PRINCIPLE OF CHARITY" in p_def

    p_arb = adversarial_system_prompt('DialecticalArbiter', 'detection')
    assert "DIALECTICAL ARBITER" in p_arb
    assert "BURDEN OF PROOF" in p_arb


def test_adversarial_schemas_and_validators():
    # Valid prosecutor
    val_pros = {
        'has_fallacy_charge': True,
        'candidate_class': 'False Dilemma',
        'defect_mechanism': 'Falsely eliminates intermediate alternatives.',
        'quote': 'Only two choices',
    }
    validate_prosecutor(val_pros, 'We have Only two choices left.')

    # Invalid quote
    with pytest.raises(ValueError, match='verbatim substring'):
        validate_prosecutor(val_pros, 'Completely different text.')

    # Valid defender
    val_def = {
        'concede_charge': False,
        'charitable_interpretation': 'Author was using colloquial emphasis, not a formal disjunction.',
        'counter_quote': 'left',
    }
    validate_defender(val_def, 'Only two choices left.')

    # Valid arbiter
    val_arb = {
        'prediction': 'Non-Fallacious',
        'confidence': 0.85,
        'content': 'Defender successfully established rhetorical context.',
    }
    validate_dialectical_arbiter(val_arb, 'detection')


def test_adversarial_execution_no_charge_dismissed():
    responses = [
        # Prosecutor: no charge
        {
            'has_fallacy_charge': False,
            'candidate_class': 'None',
            'defect_mechanism': 'No structural defect identified.',
            'quote': '',
        },
        # Arbiter: swift confirmation
        {
            'prediction': 'Non-Fallacious',
            'confidence': 0.95,
            'content': 'Target comment expresses ordinary discourse.',
        },
    ]
    llm = MockScriptedLLM(responses)
    model_input = ModelInput('Title', '', 'People should have basic equal rights.')

    engine = Engine(llm, task='detection', adaptive_policy='adversarial')
    result = engine.run(model_input, {'sample_id': '1'})

    assert result['framework'] == 'adversarial'
    assert result['prediction'] == 'Non-Fallacious'
    assert result['stop_reason'] == 'no_charge_dismissed'
    assert len(llm.call_history) == 2  # Exactly 2 calls!


def test_adversarial_execution_contested_adjudication():
    responses = [
        # Call 1: Prosecutor charges Slippery Slope
        {
            'has_fallacy_charge': True,
            'candidate_class': 'Slippery Slope',
            'defect_mechanism': 'Unwarranted domino escalation.',
            'quote': 'disaster will follow',
        },
        # Call 2: Defender plea
        {
            'concede_charge': False,
            'charitable_interpretation': 'Context proves a precedent is legally at stake.',
            'counter_quote': 'disaster will follow',
        },
        # Call 3: Arbiter verdict
        {
            'prediction': 'Fallacious',
            'confidence': 0.75,
            'content': 'Prosecutor demonstrated that intermediary links are completely missing.',
        },
    ]
    llm = MockScriptedLLM(responses)
    model_input = ModelInput('Title', '', 'If this passes, complete disaster will follow.')

    engine = Engine(llm, task='detection', adaptive_policy='adversarial')
    result = engine.run(model_input, {'sample_id': '2'})

    assert result['framework'] == 'adversarial'
    assert result['prediction'] == 'Fallacious'
    assert result['stop_reason'] == 'contested_adjudication'
    assert len(llm.call_history) == 3  # Exactly 3 calls!
