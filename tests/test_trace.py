import yaml

from src.trace import build_sample_trace, sample_trace_filename, write_sample_trace


def test_trace_has_meaningful_filename_stats_and_no_legacy_blobs(tmp_path):
    trace = build_sample_trace(
        sample={
            "id": "237:5209",
            "article_id": 237,
            "task": "detection",
            "split": "dev",
            "gold": "Non-Fallacious",
        },
        model_input={
            "title": "Title",
            "parent": "",
            "target": "I think this election is about good and evil.",
        },
        initial_analysis={
            "structure": {
                "candidate": None,
                "evidence_spans": ["good and evil"],
                "structure_type": "none",
                "slots": [],
                "structure_complete": False,
            },
            "goal": {
                "candidate": None,
                "evidence_spans": ["good and evil"],
                "conclusion_or_goal": "make a moral contrast",
                "support_mechanism": "none",
                "mechanism_supports_goal": False,
            },
            "counterargument": {
                "candidate": None,
                "evidence_spans": ["good and evil"],
                "decisive_counterargument": None,
                "failure_mode": "none",
                "failure_exposed": False,
            },
        },
        conflicts=[],
        arbiter={
            "selected_candidate": None,
            "verified": False,
            "evidence_spans": [],
            "decisive_condition": "none",
            "rejection_reason": "No candidate survived.",
        },
        stats={
            "logical_calls": 4,
            "provider_calls": 4,
            "cache_hits": 0,
            "retries": 0,
            "prompt_tokens": 10,
            "completion_tokens": 5,
            "total_tokens": 15,
            "wall_time_seconds": 1.25,
        },
    )

    path = write_sample_trace(tmp_path, trace)
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))

    assert path.name == sample_trace_filename("237:5209")
    assert path.name == "article-237__comment-5209.yaml"
    assert loaded["stats"]["logical_calls"] == 4
    text = path.read_text(encoding="utf-8")
    assert "confidence" not in text
    assert "content:" not in text
