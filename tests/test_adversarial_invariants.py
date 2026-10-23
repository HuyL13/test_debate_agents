"""Unit tests for Adversarial Dialectical Debate schemas, quote invariants, and validators.

Covers Phase 1 refactor requirements:
- Prosecutor detection: explicit dual-state invariants (charge vs no-charge).
- Prosecutor classification: strict top-2, valid target quotes, distinct classes.
- Quote normalization without silent fuzzy substitution (SequenceMatcher).
- Defender: target-only evidence policy (rejecting parent/title/article quotes).
- Defender detection & classification: strict concession vs challenge contracts.
- Arbiter & Pairwise: schema alignment with content, strict numeric non-boolean confidence.
"""

import pytest

from src.adversarial_schemas import (
    dialectical_arbiter_schema,
    arbiter_pairwise_schema,
    validate_prosecutor,
    validate_defender,
    validate_dialectical_arbiter,
    validate_arbiter_pairwise,
)
from src.data.loader import ModelInput


# ---------------------------------------------------------------------------
# 1. Prosecutor Invariants (Detection)
# ---------------------------------------------------------------------------

def test_detection_prosecutor_valid_charge():
    target = "You either support this law or you hate children."
    val = {
        'has_fallacy_charge': True,
        'candidate_class': 'False Dilemma',
        'defect_mechanism': 'Forces an artificial binary between supporting the law and hating children.',
        'quote': 'either support this law or you hate children',
    }
    validate_prosecutor(val, target, task='detection')


def test_detection_prosecutor_rejects_empty_quote_when_charged():
    target = "You either support this law or you hate children."
    val = {
        'has_fallacy_charge': True,
        'candidate_class': 'False Dilemma',
        'defect_mechanism': 'Forces an artificial binary.',
        'quote': '',
    }
    with pytest.raises(ValueError, match="quote.*must be non-empty"):
        validate_prosecutor(val, target, task='detection')


def test_detection_prosecutor_rejects_quote_not_in_target():
    target = "You either support this law or you hate children."
    val = {
        'has_fallacy_charge': True,
        'candidate_class': 'False Dilemma',
        'defect_mechanism': 'Forces an artificial binary.',
        'quote': 'you are against our great nation',
    }
    with pytest.raises(ValueError, match="verbatim substring of target comment"):
        validate_prosecutor(val, target, task='detection')


def test_detection_prosecutor_rejects_none_candidate_when_charged():
    target = "You either support this law or you hate children."
    val = {
        'has_fallacy_charge': True,
        'candidate_class': 'None',
        'defect_mechanism': 'Identified a defect.',
        'quote': 'either support this law',
    }
    with pytest.raises(ValueError, match="cannot be 'None' when has_fallacy_charge is true"):
        validate_prosecutor(val, target, task='detection')


def test_detection_prosecutor_rejects_empty_defect_mechanism():
    target = "You either support this law or you hate children."
    val = {
        'has_fallacy_charge': True,
        'candidate_class': 'False Dilemma',
        'defect_mechanism': '   ',
        'quote': 'either support this law',
    }
    with pytest.raises(ValueError, match="defect_mechanism must be a non-empty string"):
        validate_prosecutor(val, target, task='detection')


def test_detection_prosecutor_valid_no_charge():
    target = "Public infrastructure requires adequate municipal funding."
    val = {
        'has_fallacy_charge': False,
        'candidate_class': 'None',
        'defect_mechanism': 'The statement is a standard public policy claim without inferential fallacy.',
        'quote': '',
    }
    validate_prosecutor(val, target, task='detection')


def test_detection_prosecutor_requires_none_candidate_when_no_charge():
    target = "Public infrastructure requires adequate municipal funding."
    val = {
        'has_fallacy_charge': False,
        'candidate_class': 'False Dilemma',  # Contradictory: no charge but has class
        'defect_mechanism': 'No defect found.',
        'quote': '',
    }
    with pytest.raises(ValueError, match="candidate_class must be 'None' when has_fallacy_charge is false"):
        validate_prosecutor(val, target, task='detection')


def test_detection_prosecutor_requires_empty_quote_when_no_charge():
    target = "Public infrastructure requires adequate municipal funding."
    val = {
        'has_fallacy_charge': False,
        'candidate_class': 'None',
        'defect_mechanism': 'No defect found.',
        'quote': 'adequate municipal funding',  # Contradictory: no charge but quotes text
    }
    with pytest.raises(ValueError, match="quote must be empty when has_fallacy_charge is false"):
        validate_prosecutor(val, target, task='detection')


def test_detection_prosecutor_requires_explanation_when_no_charge():
    target = "Public infrastructure requires adequate municipal funding."
    val = {
        'has_fallacy_charge': False,
        'candidate_class': 'None',
        'defect_mechanism': '',
        'quote': '',
    }
    with pytest.raises(ValueError, match="defect_mechanism must be a non-empty string"):
        validate_prosecutor(val, target, task='detection')


# ---------------------------------------------------------------------------
# 2. Prosecutor Invariants (Classification)
# ---------------------------------------------------------------------------

def test_classification_prosecutor_valid_top2():
    target = "If you eat processed sugar, you will get sick and eventually die an early death."
    val = {
        'has_fallacy_charge': True,
        'candidate_class': 'Slippery Slope',
        'defect_mechanism': 'Asserts an inevitable chain of catastrophic health consequences.',
        'quote': 'eventually die an early death',
        'runner_up_class': 'Appeal to Nature',
        'runner_up_defect': 'Implicitly assumes processed sugar is dangerous purely because it is artificial.',
        'runner_up_quote': 'processed sugar',
    }
    validate_prosecutor(val, target, task='classification')


def test_classification_prosecutor_rejects_no_charge():
    target = "Some comment."
    val = {
        'has_fallacy_charge': False,
        'candidate_class': 'None',
        'defect_mechanism': 'No defect',
        'quote': '',
        'runner_up_class': 'False Dilemma',
        'runner_up_defect': 'None',
        'runner_up_quote': '',
    }
    with pytest.raises(ValueError, match="has_fallacy_charge must be true for classification"):
        validate_prosecutor(val, target, task='classification')


def test_classification_prosecutor_requires_distinct_candidate_and_runner_up():
    target = "If you eat processed sugar, you will get sick."
    val = {
        'has_fallacy_charge': True,
        'candidate_class': 'Slippery Slope',
        'defect_mechanism': 'Domino effect.',
        'quote': 'get sick',
        'runner_up_class': 'Slippery Slope',  # Duplicate
        'runner_up_defect': 'Same thing.',
        'runner_up_quote': 'get sick',
    }
    with pytest.raises(ValueError, match="runner_up_class must be different from candidate_class"):
        validate_prosecutor(val, target, task='classification')


def test_classification_prosecutor_rejects_invalid_runner_up_class():
    target = "If you eat processed sugar, you will get sick."
    val = {
        'has_fallacy_charge': True,
        'candidate_class': 'Slippery Slope',
        'defect_mechanism': 'Domino effect.',
        'quote': 'get sick',
        'runner_up_class': 'Non-Existent Fallacy',
        'runner_up_defect': 'Invalid class',
        'runner_up_quote': 'get sick',
    }
    with pytest.raises(ValueError, match="Invalid runner_up_class"):
        validate_prosecutor(val, target, task='classification')


def test_classification_prosecutor_rejects_empty_or_hallucinated_runner_up_quote():
    target = "If you eat processed sugar, you will get sick."
    val_empty = {
        'has_fallacy_charge': True,
        'candidate_class': 'Slippery Slope',
        'defect_mechanism': 'Domino effect.',
        'quote': 'get sick',
        'runner_up_class': 'Appeal to Nature',
        'runner_up_defect': 'Artificial food warning.',
        'runner_up_quote': '',
    }
    with pytest.raises(ValueError, match="runner_up_quote must be non-empty"):
        validate_prosecutor(val_empty, target, task='classification')

    val_hallucinated = {
        'has_fallacy_charge': True,
        'candidate_class': 'Slippery Slope',
        'defect_mechanism': 'Domino effect.',
        'quote': 'get sick',
        'runner_up_class': 'Appeal to Nature',
        'runner_up_defect': 'Artificial food warning.',
        'runner_up_quote': 'chemicals produced in lab factories',
    }
    with pytest.raises(ValueError, match="runner_up_quote.*not a verbatim substring"):
        validate_prosecutor(val_hallucinated, target, task='classification')


# ---------------------------------------------------------------------------
# 3. Quote Normalization & No Silent Fuzzy Replacement
# ---------------------------------------------------------------------------

def test_quote_normalized_whitespace_and_punctuation_accepted():
    target = 'The committee said: "It’s a long-standing tradition—we must keep it."'
    # Quote uses straight quotes, standard hyphen, and irregular whitespace
    quote = "It's  a long-standing tradition-we must keep it."
    val = {
        'has_fallacy_charge': True,
        'candidate_class': 'Appeal to Tradition',
        'defect_mechanism': 'Appeals to custom rather than merits.',
        'quote': quote,
    }
    # Should be accepted after whitespace and punctuation normalization
    validate_prosecutor(val, target, task='detection')


def test_quote_fuzzy_match_rejected_not_silently_repaired():
    """Verify that SequenceMatcher does NOT silently rewrite a different phrase with high lexical overlap."""
    target = "We have always done it this way for three hundred years in our county."
    # Similar wording (ratio > 0.75), but definitely not a verbatim substring
    hallucinated_quote = "We have always done it this way for four hundred years in our state."
    val = {
        'has_fallacy_charge': True,
        'candidate_class': 'Appeal to Tradition',
        'defect_mechanism': 'Tradition appeal.',
        'quote': hallucinated_quote,
    }
    with pytest.raises(ValueError, match="not a verbatim substring"):
        validate_prosecutor(val, target, task='detection')
    # Make sure val['quote'] was NOT modified to the target string
    assert val['quote'] == hallucinated_quote


# ---------------------------------------------------------------------------
# 4. Defender Invariants (Detection)
# ---------------------------------------------------------------------------

def test_detection_defender_valid_concession():
    target = "Only two choices left for us."
    val = {
        'concede_charge': True,
        'charitable_interpretation': 'Prosecutor correctly identified the forced binary choice.',
        'counter_quote': '',
    }
    validate_defender(val, target, task='detection')


def test_detection_defender_valid_challenge():
    target = "The policy will cause difficulties, but we will adapt."
    val = {
        'concede_charge': False,
        'charitable_interpretation': 'Comment acknowledges difficulties without claiming a catastrophic domino collapse.',
        'counter_quote': 'we will adapt',
    }
    validate_defender(val, target, task='detection')


def test_detection_defender_rejects_empty_quote_when_challenging():
    target = "The policy will cause difficulties, but we will adapt."
    val = {
        'concede_charge': False,
        'charitable_interpretation': 'Not a slippery slope.',
        'counter_quote': '',
    }
    with pytest.raises(ValueError, match="counter_quote must be non-empty"):
        validate_defender(val, target, task='detection')


def test_detection_defender_rejects_quote_not_in_target_comment():
    target = "The policy will cause difficulties, but we will adapt."
    val = {
        'concede_charge': False,
        'charitable_interpretation': 'Not a slippery slope.',
        'counter_quote': 'we will overcome all hurdles easily',
    }
    with pytest.raises(ValueError, match="counter_quote.*not a verbatim substring"):
        validate_defender(val, target, task='detection')


def test_detection_defender_rejects_empty_charitable_interpretation():
    target = "The policy will cause difficulties, but we will adapt."
    val = {
        'concede_charge': False,
        'charitable_interpretation': '   ',
        'counter_quote': 'we will adapt',
    }
    with pytest.raises(ValueError, match="charitable_interpretation must be a non-empty string"):
        validate_defender(val, target, task='detection')


# ---------------------------------------------------------------------------
# 5. Defender Invariants (Classification) & Target-Only Policy
# ---------------------------------------------------------------------------

def test_classification_defender_valid_concession():
    target = "This is a story as old as time."
    val = {
        'concede_charge': True,
        'alternative_class': 'None',
        'charitable_interpretation': 'The candidate class captures the reasoning defect accurately.',
        'counter_quote': '',
    }
    validate_defender(val, target, task='classification')


def test_classification_defender_concession_normalizes_alternative_to_none():
    target = "This is a story as old as time."
    val = {
        'concede_charge': True,
        'alternative_class': 'Appeal to Tradition',  # Conceding should clear alternative
        'charitable_interpretation': 'Conceding candidate.',
        'counter_quote': '',
    }
    validate_defender(val, target, task='classification')
    assert val['alternative_class'] == 'None'


def test_classification_defender_valid_challenge():
    target = "This is a story as old as time, passed down from generation to generation."
    val = {
        'concede_charge': False,
        'alternative_class': 'Appeal to Tradition',
        'charitable_interpretation': 'The comment appeals to generational transmission as authority.',
        'counter_quote': 'passed down from generation to generation',
    }
    validate_defender(val, target, task='classification')


def test_classification_defender_challenge_rejects_none_alternative():
    target = "This is a story as old as time."
    val = {
        'concede_charge': False,
        'alternative_class': 'None',
        'charitable_interpretation': 'I disagree with the prosecutor.',
        'counter_quote': 'as old as time',
    }
    with pytest.raises(ValueError, match="MUST be one of the eight fallacies"):
        validate_defender(val, target, task='classification')


def test_classification_defender_challenge_rejects_parent_comment_quote():
    """Policy invariant: Defender cannot cite parent comment as evidence for target classification."""
    model_input = ModelInput(
        title="Article Title",
        parent_comment="Dr. Fauci says we should trust the medical science.",
        comment="People on the internet are acting crazy today.",
        article="Full news article body text.",
    )
    val = {
        'concede_charge': False,
        'alternative_class': 'Appeal to Authority',
        'charitable_interpretation': 'Target is actually citing an authority.',
        'counter_quote': 'Dr. Fauci says we should trust the medical science',  # In parent, NOT in target!
    }
    with pytest.raises(ValueError, match="counter_quote.*not a verbatim substring of target comment"):
        validate_defender(val, model_input, task='classification')


def test_classification_defender_challenge_rejects_article_quote():
    """Policy invariant: Defender cannot cite article text as evidence for target classification."""
    model_input = ModelInput(
        title="Article Title",
        parent_comment="Parent discussion thread.",
        comment="People on the internet are acting crazy today.",
        article="According to researchers at Oxford University, dietary habits vary.",
    )
    val = {
        'concede_charge': False,
        'alternative_class': 'Appeal to Authority',
        'charitable_interpretation': 'Oxford research cited.',
        'counter_quote': 'researchers at Oxford University',  # In article, NOT in target!
    }
    with pytest.raises(ValueError, match="counter_quote.*not a verbatim substring of target comment"):
        validate_defender(val, model_input, task='classification')


# ---------------------------------------------------------------------------
# 6. Arbiter Invariants & Schemas
# ---------------------------------------------------------------------------

def test_arbiter_schema_requires_prediction_confidence_content():
    schema = dialectical_arbiter_schema('detection')
    assert 'prediction' in schema['required']
    assert 'confidence' in schema['required']
    assert 'content' in schema['required']


def test_arbiter_pairwise_schema_requires_prediction_confidence_content():
    schema = arbiter_pairwise_schema('False Dilemma', 'Slippery Slope')
    assert 'prediction' in schema['required']
    assert 'confidence' in schema['required']
    assert 'content' in schema['required']


def test_arbiter_validates_prediction_in_task_labels():
    val_bad = {
        'prediction': 'InvalidLabel',
        'confidence': 0.8,
        'content': 'Valid content explanation.',
    }
    with pytest.raises(ValueError, match="Arbiter prediction must be one of"):
        validate_dialectical_arbiter(val_bad, 'detection')


def test_arbiter_rejects_boolean_confidence():
    """In Python, bool is a subclass of int. Validator must explicitly forbid True/False as confidence."""
    val_true = {
        'prediction': 'Fallacious',
        'confidence': True,
        'content': 'Valid explanation.',
    }
    with pytest.raises(ValueError, match="confidence.*cannot be boolean"):
        validate_dialectical_arbiter(val_true, 'detection')

    val_false = {
        'prediction': 'Fallacious',
        'confidence': False,
        'content': 'Valid explanation.',
    }
    with pytest.raises(ValueError, match="confidence.*cannot be boolean"):
        validate_dialectical_arbiter(val_false, 'detection')


def test_arbiter_rejects_nan_and_inf_confidence():
    val_nan = {
        'prediction': 'Fallacious',
        'confidence': float('nan'),
        'content': 'Valid explanation.',
    }
    with pytest.raises(ValueError, match="confidence.*finite"):
        validate_dialectical_arbiter(val_nan, 'detection')

    val_inf = {
        'prediction': 'Fallacious',
        'confidence': float('inf'),
        'content': 'Valid explanation.',
    }
    with pytest.raises(ValueError, match="confidence.*finite"):
        validate_dialectical_arbiter(val_inf, 'detection')


def test_arbiter_rejects_out_of_bound_confidence():
    val_neg = {'prediction': 'Fallacious', 'confidence': -0.1, 'content': 'Valid.'}
    with pytest.raises(ValueError, match="between 0.0 and 1.0"):
        validate_dialectical_arbiter(val_neg, 'detection')

    val_high = {'prediction': 'Fallacious', 'confidence': 1.05, 'content': 'Valid.'}
    with pytest.raises(ValueError, match="between 0.0 and 1.0"):
        validate_dialectical_arbiter(val_high, 'detection')


def test_arbiter_populates_content_from_reasoning():
    val = {
        'prediction': 'Non-Fallacious',
        'confidence': 0.9,
        'reasoning': 'Detailed reasoning text explaining why no fallacy occurred.',
    }
    validate_dialectical_arbiter(val, 'detection')
    assert val.get('content') == 'Detailed reasoning text explaining why no fallacy occurred.'


def test_arbiter_rejects_empty_content_when_no_reasoning():
    val = {
        'prediction': 'Non-Fallacious',
        'confidence': 0.9,
        'content': '   ',
    }
    with pytest.raises(ValueError, match="content must be a non-empty string"):
        validate_dialectical_arbiter(val, 'detection')


def test_arbiter_pairwise_rejects_prediction_not_in_options():
    val = {
        'prediction': 'Appeal to Authority',
        'confidence': 0.85,
        'content': 'Chosen option.',
    }
    with pytest.raises(ValueError, match="prediction must be one of"):
        validate_arbiter_pairwise(val, 'False Dilemma', 'Slippery Slope')


def test_arbiter_pairwise_rejects_boolean_confidence():
    val = {
        'prediction': 'False Dilemma',
        'confidence': True,
        'content': 'Chosen option.',
    }
    with pytest.raises(ValueError, match="confidence.*cannot be boolean"):
        validate_arbiter_pairwise(val, 'False Dilemma', 'Slippery Slope')
