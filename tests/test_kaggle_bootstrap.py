import hashlib
import json
from pathlib import Path
import pytest

from scripts.prepare_courtroom_kaggle import serialize_pinned, prepare_classification


def test_cross_platform_serialization_preserves_pinned_bytes():
    rows = [{'comment': 'A\nB', 'gold': 'Appeal to Nature'}]
    expected = (json.dumps(rows, ensure_ascii=False, indent=2)+'\n').replace('\n', '\r\n').encode()
    assert serialize_pinned(rows, hashlib.sha256(expected).hexdigest()) == expected
    with pytest.raises(ValueError, match='checksum'):
        serialize_pinned(rows, '0'*64)


def test_prepare_filters_none_preserves_context_and_rejects_corruption(tmp_path):
    target = tmp_path / 'data/cocolofa/classification'
    target.mkdir(parents=True)
    source = tmp_path/'upstream'
    source.mkdir()
    raw = [{'id': 1, 'title': 'Title', 'content': '', 'comments': [
        {'id': 'a', 'news_id': 1, 'fallacy': 'none', 'respond_to': '', 'comment': 'Parent'},
        {'id': 'b', 'news_id': 1, 'fallacy': 'appeal to tradition', 'respond_to': 'a', 'comment': 'Old practice'}]}]
    flat = [{'sample_id': '1:b', 'article_id': 1, 'gold': 'Appeal to Tradition',
             'title': 'Title', 'parent_comment': 'Parent', 'comment': 'Old practice'}]
    raw_bytes = json.dumps(raw).encode()
    flat_bytes = (json.dumps(flat,ensure_ascii=False,indent=2)+'\n').replace('\n','\r\n').encode()
    provenance = {'commit': 'test', 'splits': {s: {'count': 1,
        'source_sha256': hashlib.sha256(raw_bytes).hexdigest(),
        'sha256': hashlib.sha256(flat_bytes).hexdigest()} for s in ('train','dev','test')}}
    (target/'provenance.json').write_text(json.dumps(provenance))
    for split in provenance['splits']:
        (source/(split+'.json')).write_bytes(raw_bytes)
    prepare_classification(tmp_path, source)
    provenance = json.loads((target/'provenance.json').read_text())
    for split in ('train', 'dev', 'test'):
        path = target/(split+'.json')
        assert hashlib.sha256(path.read_bytes()).hexdigest() == provenance['splits'][split]['sha256']
        assert json.loads(path.read_bytes()) == flat
    (target/'train.json').write_text('[]')
    with pytest.raises(ValueError, match='checksum'):
        prepare_classification(tmp_path, source)
