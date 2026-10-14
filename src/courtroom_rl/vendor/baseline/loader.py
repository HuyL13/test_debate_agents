import json
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path

from src.labels import FALLACIES, labels_for


class _PlainText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.hidden = 0

    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style'):
            self.hidden += 1
        elif tag in ('p', 'div', 'br', 'li', 'h1', 'h2', 'h3', 'blockquote'):
            self.parts.append('\n')

    def handle_endtag(self, tag):
        if tag in ('script', 'style'):
            self.hidden = max(0, self.hidden - 1)
        elif tag in ('p', 'div', 'li', 'blockquote'):
            self.parts.append('\n')

    def handle_data(self, data):
        if not self.hidden:
            self.parts.append(data)


def plain_text(html):
    parser = _PlainText()
    parser.feed(html)
    return '\n'.join(line.strip() for line in ''.join(parser.parts).splitlines() if line.strip())


@dataclass(frozen=True)
class ModelInput:
    """Only allowlisted model-visible text; no labels or annotation metadata."""
    title: str
    parent_comment: str
    comment: str
    article: str | None = None

    def as_dict(self):
        result = {'title': self.title, 'parent_comment': self.parent_comment, 'comment': self.comment}
        if self.article is not None:
            result['article'] = self.article
        return result


@dataclass(frozen=True)
class Sample:
    sample_id: str
    article_id: int
    comment_id: str
    split: str
    title: str
    comment: str
    parent_comment: str
    article: str
    fallacy: str
    missing_parent: bool

    def gold(self, task):
        labels_for(task)
        if task == 'detection':
            return 'Non-Fallacious' if self.fallacy == 'none' else 'Fallacious'
        if self.fallacy == 'none':
            raise ValueError('Classification requires a gold-positive sample')
        return self.fallacy

    def model_input(self, context='paper'):
        if context not in ('paper', 'article', 'comment_only'):
            raise ValueError(f'Unknown context: {context}')
        return ModelInput(
            self.title if context != 'comment_only' else '',
            self.parent_comment if context != 'comment_only' else '', self.comment,
            plain_text(self.article) if context == 'article' else None)


def load_split(path):
    path = Path(path)
    raw = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(raw, list) or not raw:
        raise ValueError('Split must be a non-empty list of articles or samples')
    mapping = {label.lower(): label for label in FALLACIES}
    mapping['none'] = 'none'

    # Support flat records (e.g. diagnostic error splits like dev_classification_errors/dev.json)
    if 'comments' not in raw[0]:
        samples, seen_sids = [], set()
        for r in raw:
            sid = str(r.get('sample_id', r.get('id', '')))
            if not sid or sid in seen_sids:
                raise ValueError(f'Invalid or duplicate sample ID: {sid}')
            seen_sids.add(sid)
            aid = r.get('article_id', int(sid.split(':')[0]) if ':' in sid and sid.split(':')[0].isdigit() else 0)
            cid = sid.split(':')[1] if ':' in sid else sid
            fallacy_raw = str(r.get('gold', r.get('fallacy', r.get('label', 'none'))))
            fallacy = mapping.get(fallacy_raw.lower(), 'none')
            samples.append(Sample(
                sample_id=sid,
                article_id=aid,
                comment_id=cid,
                split=path.stem,
                title=r.get('title', ''),
                comment=r.get('comment', ''),
                parent_comment=r.get('parent_comment', '') or '',
                article=r.get('article', '') or '',
                fallacy=fallacy,
                missing_parent=bool(r.get('parent_comment') is None),
            ))
        return samples

    articles = raw
    samples, article_ids, comment_ids = [], set(), set()
    for article in articles:
        aid = article['id']
        if type(aid) is not int or aid in article_ids:
            raise ValueError(f'Invalid or duplicate article ID: {aid}')
        article_ids.add(aid)
        comments = article['comments']
        if not isinstance(comments, list) or not comments:
            raise ValueError(f'Article {aid} has no comments')
        by_id = {c['id']: c for c in comments}
        for c in comments:
            cid = c['id']
            if not isinstance(cid, str) or not cid or cid in comment_ids:
                raise ValueError(f'Invalid or duplicate comment ID: {cid}')
            comment_ids.add(cid)
            if type(c['news_id']) is not int or c['news_id'] != aid:
                raise ValueError(f'Wrong news_id for comment {cid}')
            if c['fallacy'] not in mapping:
                raise ValueError(f'Unknown upstream fallacy: {c["fallacy"]}')
            for value in (article['title'], article['content'], c['comment'], c['respond_to']):
                if not isinstance(value, str):
                    raise ValueError(f'Non-string text field in {aid}:{cid}')
            parent_id = c['respond_to']
            if parent_id == cid:
                raise ValueError(f'Self-referencing parent: {cid}')
            parent = by_id.get(parent_id)
            samples.append(Sample(f'{aid}:{cid}', aid, cid, path.stem, article['title'],
                                  c['comment'], parent['comment'] if parent else '',
                                  article['content'], mapping[c['fallacy']],
                                  bool(parent_id and parent is None)))
    return samples


def select_task(samples, task):
    labels_for(task)
    return [s for s in samples if task == 'detection' or s.fallacy != 'none']
