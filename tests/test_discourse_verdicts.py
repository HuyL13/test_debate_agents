import pytest

from src.discourse_classification.pipeline import candidate_status, validate_anchor, recovery_anchor
from src.discourse_classification.runner import summarize


def test_defect_is_skipped_when_reasoning_is_not_used():
    assert candidate_status({'ownership': 'MENTIONS_OR_REJECTS', 'mechanism': 'PRESENT', 'defect': None}) == 'rejected'
    assert candidate_status({'ownership': 'USES', 'mechanism': 'ABSENT', 'defect': None}) == 'rejected'
    with pytest.raises(ValueError):
        candidate_status({'ownership': 'USES', 'mechanism': 'PRESENT', 'defect': None})


def test_unclear_is_not_absent_or_confirmed():
    assert candidate_status({'ownership': 'USES', 'mechanism': 'UNCLEAR', 'defect': None}) == 'uncertain'
    assert candidate_status({'ownership': 'USES', 'mechanism': 'PRESENT', 'defect': 'UNCLEAR'}) == 'uncertain'
    assert candidate_status({'ownership': 'USES', 'mechanism': 'PRESENT', 'defect': 'PRESENT'}) == 'confirmed'


def test_bridge_is_code_owned_and_present_mechanism_needs_roles():
    candidate = {'label': 'Slippery Slope', 'nodes': ['P1', 'P2']}
    result = {'mechanism': 'PRESENT', 'premise_node_ids': ['P1'], 'conclusion_node_ids': ['P2']}
    validate_anchor(candidate, result)
    result['conclusion_node_ids'] = []
    with pytest.raises(ValueError):
        validate_anchor(candidate, result)


def test_uncertain_recovery_is_counted_in_metrics():
    row = {'sample_id': '1', 'status': 'ok', 'task': 'classification', 'gold': 'Slippery Slope', 'prediction': 'Slippery Slope',
           'decision_mode': 'recovery_uncertain', 'candidates': []}
    assert summarize([row], False, 'graph')['recovery_count'] == 1


def test_recovery_cannot_collapse_multinode_anchor_to_one_role():
    candidates = [{'label': 'Slippery Slope', 'nodes': ['P1', 'P2']}]
    proposal = {'label': 'Slippery Slope', 'premise_node_ids': ['P1'], 'conclusion_node_ids': ['P1']}
    with pytest.raises(ValueError, match='distinct'):
        recovery_anchor(candidates, proposal)
