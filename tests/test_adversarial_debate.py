"""Unit tests for Adversarial Dialectical Debate (Prosecutor vs. Defender)."""

import pytest

from src.adversarial_prompts import adversarial_system_prompt
from src.adversarial_schemas import (
    validate_prosecutor,
    validate_defender,
    validate_dialectical_arbiter,
)
from src.engine import Engine
from src.data.loader import ModelInput


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
    assert "CUE SCAN" in p_pros
    assert "runner_up_class" in p_pros

    p_def = adversarial_system_prompt('Defender', 'classification')
    assert "DEFENDER" in p_def
    assert "TWO-WAY DISAMBIGUATION RULES" in p_def
    assert "HASTY GENERALIZATION (HG) vs. FALSE DILEMMA (FD)" in p_def

    p_arb = adversarial_system_prompt('DialecticalArbiter', 'classification')
    assert "DIALECTICAL ARBITER" in p_arb
    assert "CUE LOCKING PRINCIPLE" in p_arb
    assert "BURDEN OF PROOF" in p_arb


def test_adversarial_classification_schemas_and_validators():
    target_text = 'People are dying in the streets, so ignore this minor complaint.'
    # Valid prosecutor for classification (top-2 with quotes)
    val_pros = {
        'has_fallacy_charge': True,
        'candidate_class': 'Appeal to Worse Problems',
        'defect_mechanism': 'Deflects from the local issue by pointing to a worse crisis.',
        'quote': 'dying in the streets',
        'runner_up_class': 'False Dilemma',
        'runner_up_defect': 'Presents false either-or between dying and minor complaint.',
        'runner_up_quote': 'minor complaint',
    }
    validate_prosecutor(val_pros, target_text, task='classification')

    # Invalid candidate_class for classification ('None' not allowed)
    bad_pros = {
        'has_fallacy_charge': True,
        'candidate_class': 'None',
        'defect_mechanism': 'None',
        'quote': 'dying in the streets',
        'runner_up_class': 'False Dilemma',
        'runner_up_defect': 'Defect',
        'runner_up_quote': 'minor complaint',
    }
    with pytest.raises(ValueError, match='Invalid candidate_class'):
        validate_prosecutor(bad_pros, target_text, task='classification')

    # Invalid runner_up_class (identical to candidate_class)
    bad_ru_same = {
        'has_fallacy_charge': True,
        'candidate_class': 'Appeal to Worse Problems',
        'defect_mechanism': 'Deflects from local issue.',
        'quote': 'dying in the streets',
        'runner_up_class': 'Appeal to Worse Problems',
        'runner_up_defect': 'Same class',
        'runner_up_quote': 'minor complaint',
    }
    with pytest.raises(ValueError, match='runner_up_class must be different'):
        validate_prosecutor(bad_ru_same, target_text, task='classification')

    # Valid defender challenging prosecutor in classification
    val_def = {
        'concede_charge': False,
        'alternative_class': 'Appeal to Tradition',
        'charitable_interpretation': 'Comment argues based on ancient custom, not an inductive sample leap.',
        'counter_quote': 'as old as time',
    }
    validate_defender(val_def, 'This is a story as old as time.', task='classification')

    # Invalid defender: concede_charge is false, but alternative_class is 'None'
    bad_def_none = {
        'concede_charge': False,
        'alternative_class': 'None',
        'charitable_interpretation': 'Disagrees without an alternative',
        'counter_quote': 'as old as time',
    }
    with pytest.raises(ValueError, match='MUST be one of the eight fallacies'):
        validate_defender(bad_def_none, 'This is a story as old as time.', task='classification')

    # Invalid defender: counter_quote not in text
    bad_def_quote = {
        'concede_charge': False,
        'alternative_class': 'Appeal to Tradition',
        'charitable_interpretation': 'Disagrees with charge',
        'counter_quote': 'hallucinated phrase not in comment',
    }
    with pytest.raises(ValueError, match='Defender counter_quote'):
        validate_defender(bad_def_quote, 'This is a story as old as time.', task='classification')

    # Valid arbiter for classification
    val_arb = {
        'prediction': 'Appeal to Tradition',
        'confidence': 0.90,
        'content': 'Defender correctly identified Appeal to Tradition via norm/custom cue.',
    }
    validate_dialectical_arbiter(val_arb, task='classification')


def test_adversarial_classification_execution_contested():
    responses = [
        # Call 1: Prosecutor top-2 (candidate: Hasty Generalization, runner-up: Appeal to Tradition)
        {
            'has_fallacy_charge': True,
            'candidate_class': 'Hasty Generalization',
            'defect_mechanism': 'Broad claim about traditions.',
            'quote': 'story as old as time',
            'runner_up_class': 'Appeal to Tradition',
            'runner_up_defect': 'Chronological justification.',
            'runner_up_quote': 'almost tradition at this point',
        },
        # Call 2: Defender steelmans runner-up Appeal to Tradition with distinct >= 5-word quote & cue
        {
            'concede_charge': False,
            'alternative_class': 'Appeal to Tradition',
            'charitable_interpretation': 'Target has norm/custom cue "almost tradition at this point", satisfying Tradition.',
            'counter_quote': 'almost tradition at this point',
        },
        # Call 3: Arbiter Run A (Cand vs Alt) -> rules Appeal to Tradition
        {
            'prediction': 'Appeal to Tradition',
            'confidence': 0.92,
            'content': 'Run A: The cue scan finds norm/custom cue matching Appeal to Tradition.',
        },
        # Call 4: Arbiter Run B (Alt vs Cand) -> rules Appeal to Tradition
        {
            'prediction': 'Appeal to Tradition',
            'confidence': 0.90,
            'content': 'Run B: Swapped order agrees on Appeal to Tradition.',
        },
    ]
    llm = MockScriptedLLM(responses)
    model_input = ModelInput('News Title', '', "It's almost tradition at this point, a story as old as time.")

    engine = Engine(llm, task='classification', adaptive_policy='adversarial')
    result = engine.run(model_input, {'sample_id': '19:9353'})

    assert result['framework'] == 'adversarial'
    assert result['prediction'] == 'Appeal to Tradition'
    assert result['stop_reason'] == 'contested_classification'
    assert len(llm.call_history) == 4


def test_adversarial_classification_execution_contested_disagreement():
    responses = [
        # Call 1: Prosecutor top-2
        {
            'has_fallacy_charge': True,
            'candidate_class': 'Hasty Generalization',
            'defect_mechanism': 'Broad claim.',
            'quote': 'story as old as time',
            'runner_up_class': 'Appeal to Tradition',
            'runner_up_defect': 'Tradition cue.',
            'runner_up_quote': 'almost tradition at this point',
        },
        # Call 2: Defender plea
        {
            'concede_charge': False,
            'alternative_class': 'Appeal to Tradition',
            'charitable_interpretation': 'Tradition cue present.',
            'counter_quote': 'almost tradition at this point',
        },
        # Call 3: Arbiter Run A -> votes Appeal to Tradition
        {
            'prediction': 'Appeal to Tradition',
            'confidence': 0.85,
            'content': 'Run A supports Tradition.',
        },
        # Call 4: Arbiter Run B -> votes Hasty Generalization (disagreement / order bias!)
        {
            'prediction': 'Hasty Generalization',
            'confidence': 0.80,
            'content': 'Run B upholds Candidate.',
        },
    ]
    llm = MockScriptedLLM(responses)
    model_input = ModelInput('News Title', '', "It's almost tradition at this point, a story as old as time.")

    engine = Engine(llm, task='classification', adaptive_policy='adversarial')
    result = engine.run(model_input, {'sample_id': '19:9353'})

    assert result['framework'] == 'adversarial'
    # Burden of proof not met: candidate stands!
    assert result['prediction'] == 'Hasty Generalization'
    assert result['stop_reason'] == 'contested_classification'
    assert len(llm.call_history) == 4



def test_adversarial_classification_execution_agreed():
    responses = [
        # Call 1: Prosecutor top-2
        {
            'has_fallacy_charge': True,
            'candidate_class': 'False Dilemma',
            'defect_mechanism': 'Forced binary choice.',
            'quote': 'either with us or against us',
            'runner_up_class': 'Hasty Generalization',
            'runner_up_defect': 'Universal assumption.',
            'runner_up_quote': 'with us',
        },
        # Call 2: Defender concedes (no competing quote exists)
        {
            'concede_charge': True,
            'alternative_class': 'None',
            'charitable_interpretation': 'Prosecutor correctly identified the forced dichotomy; no competing quote exists.',
            'counter_quote': 'either with us or against us',
        },
        # Call 3: Arbiter confirms
        {
            'prediction': 'False Dilemma',
            'confidence': 0.95,
            'content': 'Both agents concur on the binary forced choice matching OPTION cue.',
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


def test_fallacy_cues_and_defender_validator():
    from src.fallacy_cues import (
        has_class_cue,
        is_cue_locked,
        validate_and_normalize_defender,
    )

    # 1. Cue matching tests
    assert has_class_cue('Appeal to Authority', 'Dr. Smith, lead scientist at the university, said it is safe')
    assert not has_class_cue('Appeal to Authority', 'People are angry at the government')
    assert has_class_cue('Appeal to Tradition', 'We have always done it this way for centuries')
    assert not has_class_cue('Appeal to Tradition', 'Yesterday I saw a car crash')
    assert has_class_cue('Appeal to Worse Problems', 'Why care about bike lanes when children are starving in the streets?')
    assert not has_class_cue('Appeal to Worse Problems', 'Things will only get worse tomorrow')
    assert has_class_cue('False Dilemma', 'You are either with us or against us, pick one')
    assert has_class_cue('Slippery Slope', 'If we allow this, it will inevitably lead to total collapse')

    # 2. Cue locking
    assert is_cue_locked('Appeal to Authority', 'Dr. Fauci confirmed the finding')
    assert is_cue_locked('Appeal to Tradition', 'Traditional ceremony held for 300 years')
    assert not is_cue_locked('Slippery Slope', 'This can only lead to disaster')

    # 3. Defender validator normalizations
    prosecutor = {
        'candidate_class': 'Appeal to Authority',
        'quote': 'Dr. Katherine Wood confirmed the vaccine formula is unstable',
    }
    comment = 'Dr. Katherine Wood confirmed the vaccine formula is unstable. Things are bad.'

    # Case A: alt == candidate -> concede
    def_same = {
        'concede_charge': False,
        'alternative_class': 'Appeal to Authority',
        'counter_quote': 'confirmed the vaccine formula is unstable',
    }
    norm_same = validate_and_normalize_defender(prosecutor, def_same, comment)
    assert norm_same['concede_charge'] is True
    assert norm_same['alternative_class'] == 'None'

    # Case B: identical quote -> concede
    def_ident = {
        'concede_charge': False,
        'alternative_class': 'Slippery Slope',
        'counter_quote': 'Dr. Katherine Wood confirmed the vaccine formula is unstable',
    }
    norm_ident = validate_and_normalize_defender(prosecutor, def_ident, comment)
    assert norm_ident['concede_charge'] is True
    assert norm_ident['alternative_class'] == 'None'

    # Case C: short quote (< 3 words) -> concede
    comment_short = 'Dr. Katherine Wood confirmed the formula. Too short.'
    def_short = {
        'concede_charge': False,
        'alternative_class': 'Slippery Slope',
        'counter_quote': 'Too short',
    }
    norm_short = validate_and_normalize_defender(prosecutor, def_short, comment_short)
    assert norm_short['concede_charge'] is True
    assert norm_short['alternative_class'] == 'None'

    # Case D: quote lacking alternative cue -> concede
    comment_long = 'Dr. Wood said it is safe. Today is Tuesday and the sky is blue outside.'
    def_no_cue = {
        'concede_charge': False,
        'alternative_class': 'Appeal to Tradition',
        'counter_quote': 'Today is Tuesday and the sky is blue',
    }
    norm_no_cue = validate_and_normalize_defender(prosecutor, def_no_cue, comment_long)
    assert norm_no_cue['concede_charge'] is True
    assert norm_no_cue['alternative_class'] == 'None'

