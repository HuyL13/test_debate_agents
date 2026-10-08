import json
import random
from pathlib import Path

from src.data.loader import load_split, select_task
from src.labels import FALLACIES


def load_records(path, context='paper'):
    raw = json.loads(Path(path).read_text(encoding='utf-8-sig'))
    if isinstance(raw, list) and raw and 'comments' in raw[0]:
        return [{'sample_id': s.sample_id, 'article_id': s.article_id, 'gold': s.gold('classification'),
                 **s.model_input(context).as_dict()} for s in select_task(load_split(path), 'classification')]
    if not isinstance(raw, list) or not raw:
        raise ValueError('Input must be a nonempty JSON list of articles or classification records')
    result, seen = [], set()
    for row in raw:
        label = row.get('gold', row.get('fallacy', row.get('label')))
        label = next((x for x in FALLACIES if isinstance(label, str) and x.lower() == label.lower()), None)
        sid = str(row.get('sample_id', row.get('id', '')))
        if not label or not sid or sid in seen or not isinstance(row.get('comment'), str) or not row['comment'].strip():
            raise ValueError('Records need unique sample_id/id, nonempty comment and one of eight gold/fallacy/label values')
        seen.add(sid)
        result.append({'sample_id': sid, 'article_id': row.get('article_id', row.get('news_id')),
                       'gold': label, 'comment': row['comment'],
                       'title': row.get('title', '') if context != 'comment_only' else '',
                       'parent_comment': row.get('parent_comment', '') if context != 'comment_only' else ''})
    return result


def partition(rows, validation_fraction=.2, seed=42):
    if not 0 < validation_fraction < 1:
        raise ValueError('validation_fraction must be between zero and one')
    if any(r.get('article_id') is None for r in rows):
        raise ValueError('Article-disjoint partition requires article_id/news_id on every record')
    articles = sorted({r['article_id'] for r in rows}, key=str)
    if len(articles) < 2:
        raise ValueError('Partition requires at least two articles')
    random.Random(seed).shuffle(articles)
    held = set(articles[:max(1, min(len(articles)-1, round(len(articles)*validation_fraction)))])
    return [r for r in rows if r['article_id'] not in held], [r for r in rows if r['article_id'] in held]
