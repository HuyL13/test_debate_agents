import json

import pytest

from scripts.prepare_classification_data import prepare


def test_classification_export_preserves_split_and_none_parent_context(tmp_path):
    for i, split in enumerate(('train', 'dev', 'test'), 1):
        article = {'id': i, 'title': 'Title', 'content': 'Article', 'comments': [
            {'id': 'parent', 'news_id': i, 'comment': 'Parent context', 'respond_to': '', 'fallacy': 'none'},
            {'id': 'child', 'news_id': i, 'comment': 'Natural is good', 'respond_to': 'parent', 'fallacy': 'appeal to nature'},
        ]}
        (tmp_path / f'{split}.json').write_text(json.dumps([article]))
    prepare(tmp_path)
    for i, split in enumerate(('train', 'dev', 'test'), 1):
        rows = json.loads((tmp_path / 'classification' / f'{split}.json').read_text())
        assert len(rows) == 1
        assert rows[0]['sample_id'] == f'{i}:child'
        assert rows[0]['parent_comment'] == 'Parent context'
        assert rows[0]['gold'] == 'Appeal to Nature'
    prepare(tmp_path)  # Existing identical data is safe to reuse.
    (tmp_path / 'classification/train.json').write_text('[]')
    with pytest.raises(ValueError, match='Refusing to overwrite'):
        prepare(tmp_path)
