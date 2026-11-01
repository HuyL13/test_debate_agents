from copy import deepcopy
import math

import pytest

from src.game_evaluation import evaluate_game
from src.labels import FALLACIES


def fixture():
    c, d, other = 'Appeal to Authority', 'Hasty Generalization', 'Appeal to Nature'
    rows = []
    for i, (initial, final) in enumerate([(c, d), (d, c), (c, other), (d, d)]):
        rows.append({'sample_id': str(i), 'task': 'classification', 'status': 'ok',
                     'gold': d, 'prediction': final, 'prosecutor': {'candidate_class': initial},
                     'defender_review': {'action': 'request_comparison'}, 'arbiter': {}})
    return rows


def test_utility_counts_corrections_damage_and_wrong_to_wrong_separately():
    result = evaluate_game(fixture(), benefit=2, harm=3, token_penalty=.01, total_tokens=100)
    assert result['counts'] == {'beneficial': 1, 'harmful': 1, 'wrong_to_wrong': 1, 'unchanged': 1}
    assert result['net_corrections'] == 0
    assert result['utility_total'] == -2
    assert result['utility_per_sample'] == -.5
    assert result['final']['accuracy'] == .5
    assert result['forecast_count'] == 0


def test_unconditional_eight_class_brier_and_log_loss():
    rows = fixture()[:1]
    rows[0]['arbiter']['probabilities'] = {c: int(c == rows[0]['gold']) for c in FALLACIES}
    result = evaluate_game(rows)
    assert result['mean_brier'] == 0 and result['mean_log_loss'] == 0
    rows[0]['arbiter']['probabilities'] = {c: .125 for c in FALLACIES}
    result = evaluate_game(rows)
    assert result['mean_brier'] == .875
    assert result['mean_log_loss'] == pytest.approx(math.log(8))


@pytest.mark.parametrize('weights', [{'harm': -1}, {'benefit': float('nan')}, {'token_penalty': float('inf')},
                                    {'total_tokens': -1}, {'benefit': True}])
def test_invalid_utility_parameters_fail(weights):
    with pytest.raises(ValueError):
        evaluate_game(fixture(), **weights)


def test_failed_samples_duplicates_and_invalid_forecasts_are_not_dropped():
    rows = fixture(); rows[0]['status'] = 'error'
    with pytest.raises(ValueError, match='Failed samples'):
        evaluate_game(rows)
    rows = fixture(); rows.append(deepcopy(rows[0]))
    with pytest.raises(ValueError, match='Duplicate'):
        evaluate_game(rows)
    rows = fixture(); rows[0]['arbiter']['probabilities'] = {c: .5 for c in FALLACIES}
    with pytest.raises(ValueError, match='eight-class forecast'):
        evaluate_game(rows)
