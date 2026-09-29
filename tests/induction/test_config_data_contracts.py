import json
import os
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
        "sample_id": sample["sample_id"],
        "original_text": sample["comment"],
        "canonical_reasoning": (
            "A long-standing practice is treated as evidence of stability and legitimacy "
            "because it has persisted, so replacing it should be resisted or approached cautiously."
        ),
    }


def test_config_resolves_repo_relative_data_path(tmp_path):
    config = config_for(tmp_path / "train.json")
    assert config.label == "Appeal to Tradition"
    assert config.data_path == (tmp_path / "train.json").resolve()
    assert config.embedding_model == "sentence-transformers/all-mpnet-base-v2"


def test_config_exposes_induction_completion_budget(tmp_path):
    config = load_config_from_mapping({
        "base_dir": str(tmp_path),
        "data": {"path": "train.json", "label": "appeal to tradition"},
        "llm": {"max_completion_tokens": 4096},
    })

    assert config.llm_max_completion_tokens == 4096


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


def test_semantic_validation_rejects_removed_semantic_fields(tmp_path):
    path = write_fixture_split(tmp_path / "train.json")
    sample = load_positive_samples(config_for(path))[0][0]
    record = valid_semantic_record(sample)
    record["conclusion"] = "The practice should continue."

    with pytest.raises(ValueError):
        validate_semantic_record(record, sample)


def test_semantic_validation_rejects_short_canonical_reasoning(tmp_path):
    path = write_fixture_split(tmp_path / "train.json")
    sample = load_positive_samples(config_for(path))[0][0]
    record = valid_semantic_record(sample)
    record["canonical_reasoning"] = "PRACTICE -> CHANGE"

    with pytest.raises(ValueError, match="canonical_reasoning"):
        validate_semantic_record(record, sample)


def test_semantic_validation_rejects_obvious_topic_leakage(tmp_path):
    path = write_fixture_split(tmp_path / "train.json")
    sample = load_positive_samples(config_for(path))[0][0]
    sample["comment"] = "Maine's council should preserve its old practice."
    record = valid_semantic_record(sample)
    record["canonical_reasoning"] = "Maine's council should preserve the practice."
    record["original_text"] = sample["comment"]

    with pytest.raises(ValueError, match="topic leakage"):
        validate_semantic_record(record, sample)


def test_semantic_validation_allows_generic_detopicalized_reasoning(tmp_path):
    path = write_fixture_split(tmp_path / "train.json")
    sample = load_positive_samples(config_for(path))[0][0]
    sample["comment"] = "A practice has persisted, and stronger intervention may be needed to overcome resistance."
    record = valid_semantic_record(sample)
    record["original_text"] = sample["comment"]
    record["canonical_reasoning"] = "From a long-standing practice, stronger intervention may be needed to overcome resistance."

    validate_semantic_record(record, sample)


def test_semantic_validation_ignores_sentence_initial_generic_words(tmp_path):
    path = write_fixture_split(tmp_path / "train.json")
    sample = load_positive_samples(config_for(path))[0][0]
    sample["comment"] = "A practice has persisted for a long time."
    record = valid_semantic_record(sample)
    record["original_text"] = sample["comment"]
    record["canonical_reasoning"] = (
        "Hopefully, a long-standing practice should continue because it has remained stable."
    )

    validate_semantic_record(record, sample)


def test_semantic_validation_rejects_mechanical_placeholder_templates(tmp_path):
    path = write_fixture_split(tmp_path / "train.json")
    sample = load_positive_samples(config_for(path))[0][0]
    record = valid_semantic_record(sample)
    record["canonical_reasoning"] = (
        "GROUP + TRADITIONAL_NORM + ENFORCEMENT_SYSTEM + PRACTICE + CHANGE + OUTCOME + POLICY + ACTION"
    )

    with pytest.raises(ValueError, match="uppercase placeholders|natural-language"):
        validate_semantic_record(record, sample)


def test_semantic_validation_rejects_bare_variable_placeholders(tmp_path):
    path = write_fixture_split(tmp_path / "train.json")
    sample = load_positive_samples(config_for(path))[0][0]
    record = valid_semantic_record(sample)
    record["canonical_reasoning"] = "A harmful practice persists, so X should change."

    with pytest.raises(ValueError, match="role-specific placeholders"):
        validate_semantic_record(record, sample)


def test_semantic_validation_accepts_role_specific_change_record(tmp_path):
    path = write_fixture_split(tmp_path / "train.json")
    sample = load_positive_samples(config_for(path))[0][0]
    sample["comment"] = (
        "Sad to say, I have to agree with you. Rulers concealing information from those they rule "
        "is basically tradition at this point. As you say, why would government officials ever willingly "
        "be held accountable for their misdeeds? Laws and enforcement mechanisms need to be far stronger "
        "to overcome the timeless practice of corruption."
    )
    record = {
        "sample_id": sample["sample_id"],
        "original_text": sample["comment"],
        "canonical_reasoning": (
            "A harmful PRACTICE has persisted for a long time because those responsible avoid accountability "
            "-> its persistence indicates entrenched harm rather than legitimacy "
            "-> strengthen intervention to change the PRACTICE."
        ),
    }

    validate_semantic_record(record, sample)


def test_load_config_loads_repo_dotenv_for_hf_and_llm(tmp_path, monkeypatch):
    configs = tmp_path / "configs"
    configs.mkdir()
    config_path = configs / "induction.yaml"
    config_path.write_text("data:\n  path: train.json\n  label: appeal to tradition\n", encoding="utf-8")
    (tmp_path / ".env").write_text("HF_TOKEN=hf_test\nNVIDIA_API_KEY=api_test\n", encoding="utf-8")
    monkeypatch.delenv("HF_TOKEN", raising=False)
    monkeypatch.delenv("NVIDIA_API_KEY", raising=False)
    load_config(config_path)
    assert os.environ["HF_TOKEN"] == "hf_test"
    assert os.environ["NVIDIA_API_KEY"] == "api_test"
