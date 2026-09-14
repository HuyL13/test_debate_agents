import csv
import os
import tempfile
from pathlib import Path

import yaml


STAT_FIELDS = (
    "logical_calls",
    "provider_calls",
    "cache_hits",
    "retries",
    "prompt_tokens",
    "completion_tokens",
    "total_tokens",
    "wall_time_seconds",
)


def sample_trace_filename(sample_id):
    article, comment = str(sample_id).split(":", 1)
    return f"article-{article}__comment-{comment}.yaml"


def build_sample_trace(*, sample, model_input, initial_analysis, conflicts, arbiter, stats):
    missing = [field for field in STAT_FIELDS if field not in stats]
    if missing:
        raise ValueError(f"Trace stats missing fields: {missing}")
    return {
        "sample": sample,
        "input": model_input,
        "initial_analysis": initial_analysis,
        "conflicts": conflicts,
        "arbiter": arbiter,
        "stats": {field: stats[field] for field in STAT_FIELDS},
    }


def write_sample_trace(directory, trace):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / sample_trace_filename(trace["sample"]["id"])
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=directory, suffix=".tmp", delete=False) as stream:
        name = stream.name
        yaml.safe_dump(trace, stream, sort_keys=False, allow_unicode=True)
    os.replace(name, path)
    return path


def append_samples_csv(path, row):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    exists = path.exists()
    fields = [
        "sample_id",
        "gold",
        "prediction",
        "correct",
        "initial_candidates",
        "conflict_count",
        "logical_calls",
        "provider_calls",
        "total_tokens",
        "wall_time_seconds",
    ]
    with path.open("a", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        if not exists:
            writer.writeheader()
        writer.writerow({field: row[field] for field in fields})


def aggregate_call_stats(results, wall_time_seconds):
    stats = {field: 0 for field in STAT_FIELDS}
    stats["wall_time_seconds"] = wall_time_seconds
    for result in results:
        call = result.stats
        stats["logical_calls"] += getattr(call, "logical_calls", 1)
        stats["provider_calls"] += getattr(call, "provider_calls", 0)
        stats["cache_hits"] += 1 if getattr(call, "cache_hit", False) else 0
        stats["retries"] += getattr(call, "retries", 0)
        stats["prompt_tokens"] += getattr(call, "prompt_tokens", 0)
        stats["completion_tokens"] += getattr(call, "completion_tokens", 0)
        stats["total_tokens"] += getattr(call, "total_tokens", 0)
    return stats
