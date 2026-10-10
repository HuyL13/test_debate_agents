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


def test_adversarial_classification_prompts():
    p_pros = adversarial_system_prompt('Prosecutor', 'classification', use_patterns=True)
    assert "PROSECUTOR" in p_pros
    assert "8-Class Closed Taxonomy" in p_pros
    assert "Slippery Slope" in p_pros

    p_def = adversarial_system_prompt('Defender', 'classification')
    assert "DEFENDER" in p_def
    assert "ANTI-HASTY-GENERALIZATION GUARD" in p_def
    assert "APPEAL TO WORSE PROBLEMS" in p_def

    p_arb = adversarial_system_prompt('DialecticalArbiter', 'classification')
    assert "DIALECTICAL ARBITER" in p_arb
    assert "BENCHMARK DISAMBIGUATION MATRIX" in p_arb


def test_adversarial_classification_schemas_and_validators():
    # Valid prosecutor for classification
    val_pros = {
        'has_fallacy_charge': True,
        'candidate_class': 'Appeal to Worse Problems',
        'defect_mechanism': 'Deflects from the local issue by pointing to a worse crisis.',
        'quote': 'dying in the streets',
    }
    validate_prosecutor(val_pros, 'People are dying in the streets, so ignore this.', task='classification')

    # Invalid candidate_class for classification ('None' not allowed)
    bad_pros = {
        'has_fallacy_charge': True,
        'candidate_class': 'None',
        'defect_mechanism': 'None',
        'quote': '',
    }
    with pytest.raises(ValueError, match='Invalid candidate_class'):
        validate_prosecutor(bad_pros, 'Some text', task='classification')

    # Valid defender challenging prosecutor in classification
    val_def = {
        'concede_charge': False,
        'alternative_class': 'Appeal to Tradition',
        'charitable_interpretation': 'Comment argues based on ancient custom, not an inductive sample leap.',
        'counter_quote': 'as old as time',
    }
    validate_defender(val_def, 'This is a story as old as time.', task='classification')

    # Invalid defender (invalid alternative class)
    bad_def = {
        'concede_charge': False,
        'alternative_class': 'InvalidFallacy',
        'charitable_interpretation': 'Not valid',
        'counter_quote': '',
    }
    with pytest.raises(ValueError, match='Invalid alternative_class'):
        validate_defender(bad_def, 'Text', task='classification')

    # Valid arbiter for classification
    val_arb = {
        'prediction': 'Appeal to Tradition',
        'confidence': 0.90,
        'content': 'Defender correctly identified Appeal to Tradition.',
    }
    validate_dialectical_arbiter(val_arb, task='classification')


def test_adversarial_classification_execution_contested():
    responses = [
        # Call 1: Prosecutor falsely charges Hasty Generalization
        {
            'has_fallacy_charge': True,
            'candidate_class': 'Hasty Generalization',
            'defect_mechanism': 'Broad claim about traditions.',
            'quote': 'as old as time',
        },
        # Call 2: Defender challenges and proposes Appeal to Tradition
        {
            'concede_charge': False,
            'alternative_class': 'Appeal to Tradition',
            'charitable_interpretation': 'Argument appeals to historical longevity rather than an empirical sample leap.',
            'counter_quote': 'as old as time',
        },
        # Call 3: Arbiter upholds Defender and rules Appeal to Tradition
        {
            'prediction': 'Appeal to Tradition',
            'confidence': 0.92,
            'content': 'The defect is strictly chronological justification, matching Appeal to Tradition.',
        },
    ]
    llm = MockScriptedLLM(responses)
    model_input = ModelInput('News Title', '', "It's almost tradition at this point, a story as old as time.")

    engine = Engine(llm, task='classification', adaptive_policy='adversarial')
    result = engine.run(model_input, {'sample_id': '19:9353'})

    assert result['framework'] == 'adversarial'
    assert result['prediction'] == 'Appeal to Tradition'
    assert result['stop_reason'] == 'contested_classification'
    assert len(llm.call_history) == 3


def test_adversarial_classification_execution_agreed():
    responses = [
        # Call 1: Prosecutor indicts False Dilemma
        {
            'has_fallacy_charge': True,
            'candidate_class': 'False Dilemma',
            'defect_mechanism': 'Forced binary choice.',
            'quote': 'either with us or against us',
        },
        # Call 2: Defender agrees with charge
        {
            'concede_charge': True,
            'alternative_class': 'None',
            'charitable_interpretation': 'Prosecutor correctly identified the forced dichotomy.',
            'counter_quote': 'either with us or against us',
        },
        # Call 3: Arbiter confirms
        {
            'prediction': 'False Dilemma',
            'confidence': 0.95,
            'content': 'Both agents concur on the binary forced choice.',
        },
    ]
    llm = MockScriptedLLM(responses)
    model_input = ModelInput('News Title', '', "You are either with us or against us.")

    engine = Engine(llm, task='classification', adaptive_policy='adversarial')
    result = engine.run(model_input, {'sample_id': '20:100'})

    assert result['framework'] == 'adversarial'
    assert result['prediction'] == 'False Dilemma'
    assert result['stop_reason'] == 'agreed_classification'
    assert len(llm.call_history) == 3
