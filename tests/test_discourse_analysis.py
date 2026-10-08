import pytest

from src.discourse_classification.analysis import full_selection_metrics, ranking_ablation
from src.discourse_classification.graph import build_graph
from src.discourse_classification.roles import match_arguments


def test_full_selection_metrics_count_unresolved_and_errors_as_false_negatives():
    a, b = 'Appeal to Authority', 'Appeal to Majority'
    rows = [{'sample_id': '1', 'gold': a, 'status': 'ok', 'prediction': a},
            {'sample_id': '2', 'gold': a, 'status': 'unresolved', 'prediction': None},
            {'sample_id': '3', 'gold': b, 'status': 'ok', 'prediction': a},
            {'sample_id': '4', 'gold': b, 'status': 'error'}]
    result = full_selection_metrics(rows)
    assert result['accuracy_all_selected'] == .25
    assert result['macro_f1_all_selected'] == .0625
    assert result['per_class_all_selected'][a] == {'support': 2, 'precision': .5, 'recall': .5, 'f1': .5}
    assert result['per_class_all_selected'][b]['recall'] == 0
    assert result['confusions'][f'{a} -> UNRESOLVED'] == 1
    assert result['confusions'][f'{b} -> ERROR'] == 1


def test_full_metrics_do_not_silently_accept_duplicate_ids():
    row = {'sample_id': '1', 'gold': 'Appeal to Nature', 'status': 'unresolved'}
    with pytest.raises(ValueError, match='Duplicate'):
        full_selection_metrics([row, row])


def test_ranking_ablation_reuses_grounded_roles_and_removes_only_graph_relations():
    text = 'An old policy. It should stay. Will we ban letters? After that will we abolish elections?'
    def e(text, role):
        return {'source': 'comment', 'text': text, 'role': role}
    arguments = [
        {'kind': 'SOURCE_JUSTIFICATION', 'basis': 'HISTORY', 'stance': 'USES', 'relation_status': 'EXPLICIT',
         'evidence': [e('An old policy', 'BASIS'), e('It should stay', 'CLAIM')]},
        {'kind': 'CONSEQUENCE', 'progression': 'ADVERSE', 'stance': 'USES', 'relation_status': 'EXPLICIT',
         'evidence': [e('Will we ban letters?', 'ACTION'), e('After that will we abolish elections?', 'OUTCOME')]},
    ]
    graph = build_graph(text)
    row = {'sample_id': '1', 'comment': text, 'graph': graph, 'status': 'ok', 'prediction': 'Slippery Slope',
           'gold': 'Slippery Slope', 'candidates': match_arguments(graph, {'comment': text}, arguments)}
    result = ranking_ablation([row])
    assert result['changed_predictions'] == 1
    assert result['accuracy_all_selected'] == 0
    assert row['graph']['relations']  # No mutation of original evidence/report.
