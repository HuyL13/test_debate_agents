from collections import Counter
from pathlib import Path

from src.data.loader import load_split
from src.io_utils import file_hash

EXPECTED = {'train': (452, 5370, 3168, 2202), 'dev': (129, 1538, 927, 611),
            'test': (67, 798, 481, 317)}
PINNED_HASHES = {
    'train': '51c9d03425ea9e065905b87d3d1f37b41fef0d09a0f37241594076282e7077a3',
    'dev': '23fd1fdc57930de5a5a05405d0c1084d447c98ece036be5e0b0c83793505ff65',
    'test': '366ae5d321616599cbe2d259a2be7bd529388d0a0107d37741dc2fa029169281',
}


def verify_dataset(directory):
    seen_articles, seen_comments = set(), set()
    result = {'splits': {}, 'article_disjoint': True, 'comment_disjoint': True, 'warnings': []}
    for split, expected in EXPECTED.items():
        path = Path(directory) / f'{split}.json'
        samples = load_split(path)
        aids, cids = {s.article_id for s in samples}, {s.comment_id for s in samples}
        if aids & seen_articles or cids & seen_comments:
            raise ValueError(f'Cross-split article/comment leakage in {split}')
        seen_articles |= aids
        seen_comments |= cids
        counts = Counter(s.fallacy for s in samples)
        stats = (len(aids), len(samples), len(samples) - counts['none'], counts['none'])
        missing = [s.sample_id for s in samples if s.missing_parent]
        result['splits'][split] = dict(zip(('articles', 'comments', 'positive', 'negative'), stats))
        result['splits'][split].update(labels=dict(sorted(counts.items())), sha256=file_hash(path),
                                       matches_published_counts=stats == expected, missing_parents=missing)
        if stats != expected:
            result['warnings'].append(f'{split}: counts differ from published {expected}; data unchanged')
        if missing:
            result['warnings'].append(f'{split}: missing parent context for {missing}; samples retained')
    return result
