import json
from pathlib import Path

import pytest

from src.induction.config import load_config, load_config_from_mapping
from src.induction.contracts import validate_semantic_record
from src.induction.data import load_positive_samples


def write_fixture_split(path: Path):
    path.write_text(json.dumps([
        {
            "id": 1,
            "title": "Example",
            "content": "Article body",
            "comments": [
                {"id": "c1", "news_id": 1, "comment": "Keep it because it is old.",
                 "respond_to": "", "fallacy": "appeal to tradition"},
                {"id": "c2", "news_id": 1, "comment": "A neutral comment.",
                 "respond_to": "", "fallacy": "none"},
            ],
        }
    ]), encoding="utf-8")
    return path


def config_for(path, label="Appeal to Tradition"):
    return load_config_from_mapping({
        "base_dir": str(path.parent),
        "data": {"path": path.name, "label": label},
        "output_dir": "output",
    })


def valid_semantic_record(sample):
    return {
        "article_id": sample["article_id"],
        "comment_id": sample["comment_id"],
        "original_text": sample["comment"],
        "premises": ["A practice has persisted for a long time."],
        "conclusion": "The practice should continue.",
        "inference_source": "longevity",
        "inference_target": "continuation",
        "bridge": "Longevity is treated as support for continued use.",
        "evidential_basis": "historical persistence",
        "premise_valence": "POSITIVE",
        "relation_polarity": "SUPPORTS_CONTINUITY",
        "conclusion_direction": "preserve",
        "missing_justification": None,
        "alternatives_suppressed": None,
        "causal_chain": None,
        "canonical_reasoning": "A long-standing practice is treated as evidence that it should continue.",
        "ambiguity_notes": None,
        "topic_leakage_check": False,
    }


def test_config_resolves_repo_relative_data_path(tmp_path):
    config = config_for(tmp_path / "train.json")
    assert config.label == "Appeal to Tradition"
    assert config.data_path == (tmp_path / "train.json").resolve()
    assert config.embedding_model == "sentence-transformers/all-mpnet-base-v2"


def test_none_label_is_rejected():
    with pytest.raises(ValueError, match="none"):
        load_config_from_mapping({"data": {"path": "train.json", "label": "none"}})


def test_positive_samples_and_stats_are_read_from_fixture(tmp_path):
    path = write_fixture_split(tmp_path / "train.json")
    samples, stats = load_positive_samples(config_for(path))
    assert [row["sample_id"] for row in samples] == ["1:c1"]
    assert stats["positive_sample_count"] == 1
    assert stats["duplicate_sample_ids"] == []


def test_semantic_validation_rejects_missing_canonical_reasoning(tmp_path):
    path = write_fixture_split(tmp_path / "train.json")
    sample = load_positive_samples(config_for(path))[0][0]
    record = valid_semantic_record(sample)
    record["canonical_reasoning"] = ""
    with pytest.raises(ValueError, match="canonical_reasoning"):
        validate_semantic_record(record, sample)
