import copy
import json

import pytest

from src.data.loader import load_split, select_task
from src.evaluate import score


def write_split(tmp_path, articles):
    path = tmp_path / 'dev.json'
    path.write_text(json.dumps(articles), encoding='utf-8')
    return path


@pytest.fixture
def articles():
    return [{'id': 42, 'title': 'TITLE', 'content': '<p>ARTICLE</p>', 'comments': [
        {'id': '1', 'news_id': 42, 'respond_to': '', 'worker_id': 999,
         'fallacy': 'none', 'comment': 'PARENT'},
        {'id': '2', 'news_id': 42, 'respond_to': '1', 'worker_id': 888,
         'fallacy': 'slippery slope', 'comment': 'TARGET'},
        {'id': '3', 'news_id': 42, 'respond_to': 'missing', 'worker_id': 777,
         'fallacy': 'false dilemma', 'comment': 'ORPHAN'},
    ]}]


def test_classification_filters_gold_and_retains_negative_parent(tmp_path, articles):
    samples = load_split(write_split(tmp_path, articles))
    selected = select_task(samples, 'classification')
    assert [s.sample_id for s in selected] == ['42:2', '42:3']
    assert selected[0].model_input().parent_comment == 'PARENT'
    assert len(select_task(samples, 'detection')) == 3
    assert selected[1].missing_parent is True
    assert selected[1].model_input().parent_comment == ''


def test_allowlisted_context_does_not_change_when_annotations_change(tmp_path, articles):
    before = load_split(write_split(tmp_path, articles))[1].model_input().as_dict()
    changed = copy.deepcopy(articles)
    changed[0]['comments'][1].update(fallacy='appeal to nature', worker_id=123)
    changed[0]['comments'][1]['annotation_rationale'] = 'SECRET'
    after = load_split(write_split(tmp_path, changed))[1].model_input().as_dict()
    assert before == after == {'title': 'TITLE', 'parent_comment': 'PARENT', 'comment': 'TARGET'}
    full = load_split(tmp_path / 'dev.json')[1].model_input('article').as_dict()
    assert full['article'] == 'ARTICLE'


@pytest.mark.parametrize('mutation', ['bad_label', 'duplicate', 'wrong_article'])
def test_rejects_corrupted_data(tmp_path, articles, mutation):
    c = articles[0]['comments'][1]
    if mutation == 'bad_label':
        c['fallacy'] = 'ad hominem'
    elif mutation == 'duplicate':
        c['id'] = '1'
    else:
        c['news_id'] = 99
    with pytest.raises(ValueError):
        load_split(write_split(tmp_path, articles))


def rows(task, pairs):
    return [{'sample_id': str(i), 'task': task, 'gold': g, 'prediction': p, 'status': 'ok'}
            for i, (g, p) in enumerate(pairs)]


def test_detection_positive_precision_recall_f1():
    result = score(rows('detection', [
        ('Fallacious', 'Fallacious'), ('Fallacious', 'Non-Fallacious'),
        ('Non-Fallacious', 'Fallacious'), ('Non-Fallacious', 'Non-Fallacious'),
        ('Fallacious', 'Fallacious')]))
    assert result['precision'] == pytest.approx(2 / 3)
    assert result['recall'] == pytest.approx(2 / 3)
    assert result['f1'] == pytest.approx(2 / 3)
    assert result['confusion_matrix'] == [[1, 1], [1, 2]]


def test_classification_macro_denominator_is_all_eight_labels():
    result = score(rows('classification', [('False Dilemma', 'False Dilemma')]))
    assert result['macro_f1'] == 0.125


@pytest.mark.parametrize('bad', ['none', 'Fallacious', '', None])
def test_invalid_classification_is_never_silently_normalized(bad):
    with pytest.raises(ValueError):
        score(rows('classification', [('False Dilemma', bad)]))


def test_metrics_reject_empty_duplicate_mixed_and_failed_rows():
    good = rows('detection', [('Fallacious', 'Fallacious')])
    for records in [[], good * 2, good + rows('classification', [('False Dilemma', 'False Dilemma')]),
                    [dict(good[0], status='error')]]:
        with pytest.raises(ValueError):
            score(records)
