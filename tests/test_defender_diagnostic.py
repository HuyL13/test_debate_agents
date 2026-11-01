"""Regression tests for grounded challenges that keyword gates used to discard."""
from copy import deepcopy

import pytest

from src.fallacy_cues import validate_and_normalize_defender


def plea(quote, alternative='Appeal to Worse Problems'):
    return {
        'concede_charge': False,
        'alternative_class': alternative,
        'counter_quote': quote,
        'charitable_interpretation': 'Premise: larger issues. Conclusion: defer this remedy. '
        'The candidate lacks exclusivity; the alternative captures the stated justification.',
    }


def test_priority_comparison_survives_missing_regex_and_preserves_report():
    quote = 'there are much bigger issues to deal with first'
    target = 'The remedy may have its place eventually, but ' + quote + '.'
    original = plea(quote)
    before = deepcopy(original)
    result = validate_and_normalize_defender(
        {'candidate_class': 'False Dilemma', 'quote': 'The remedy may have its place eventually'},
        original, target,
    )
    assert result['concede_charge'] is False
    assert result['alternative_class'] == 'Appeal to Worse Problems'
    assert result['charitable_interpretation'] == before['charitable_interpretation']
    assert result['raw_report'] == before
    assert original == before
    assert result['validation']['cue_found'] is False
    assert 'missing_lexical_cue' in result['validation']['warnings']


def test_shared_quote_can_support_a_different_diagnosis():
    quote = 'One crooked official means the whole administration is crooked'
    result = validate_and_normalize_defender(
        {'candidate_class': 'Appeal to Authority', 'quote': quote},
        plea(quote, 'Hasty Generalization'), quote,
    )
    assert result['concede_charge'] is False
    assert result['alternative_class'] == 'Hasty Generalization'
    assert result['validation']['shared_quote'] is True


@pytest.mark.parametrize('quote', ['', 'not present in target'])
def test_invalid_target_evidence_is_rejected_instead_of_becoming_concession(quote):
    with pytest.raises(ValueError, match='counter_quote'):
        validate_and_normalize_defender(
            {'candidate_class': 'False Dilemma', 'quote': 'target text'},
            plea(quote), 'target text',
        )


def test_same_label_agreement_keeps_original_reasoning_for_audit():
    original = plea('target text', 'False Dilemma')
    result = validate_and_normalize_defender(
        {'candidate_class': 'False Dilemma', 'quote': 'target text'}, original, 'target text',
    )
    assert result['concede_charge'] is True
    assert result['alternative_class'] == 'None'
    assert result['charitable_interpretation'] == original['charitable_interpretation']
    assert result['raw_report'] == original
    assert result['validation']['normalization_reason'] == 'same_class'


def test_short_grounded_quote_is_advisory_only():
    result = validate_and_normalize_defender(
        {'candidate_class': 'False Dilemma', 'quote': 'Choose this'},
        plea('bigger issues'), 'Choose this, despite bigger issues.',
    )
    assert result['concede_charge'] is False
    assert 'short_quote' in result['validation']['warnings']


def test_invalid_class_is_rejected():
    with pytest.raises(ValueError, match='eight fallacies'):
        validate_and_normalize_defender(
            {'candidate_class': 'False Dilemma', 'quote': 'target text'},
            plea('target text', 'invented label'), 'target text',
        )
