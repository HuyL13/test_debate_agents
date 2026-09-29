from collections import Counter
from dataclasses import asdict
import re

from src.data.loader import load_split


def _normalize(text):
    return " ".join(text.lower().split())


def _sample_dict(sample):
    value = asdict(sample)
    value["sample_id"] = sample.sample_id
    return value


def load_positive_samples(config):
    all_samples = load_split(config.data_path)
    positives = [sample for sample in all_samples if sample.fallacy == config.label]
    if not positives:
        raise ValueError(f"selected label has no samples: {config.label}")
    sample_ids = [sample.sample_id for sample in all_samples]
    normalized = [_normalize(sample.comment) for sample in all_samples]
    stats = {
        "dataset": str(config.data_path),
        "label": config.label,
        "article_count": len({sample.article_id for sample in all_samples}),
        "comment_count": len(all_samples),
        "positive_sample_count": len(positives),
        "duplicate_sample_ids": sorted(key for key, count in Counter(sample_ids).items() if count > 1),
        "duplicate_normalized_comments": sorted(key for key, count in Counter(normalized).items() if count > 1),
    }
    return [_sample_dict(sample) for sample in positives], stats

