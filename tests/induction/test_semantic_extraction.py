import json
from types import SimpleNamespace

import pytest

from src.induction.prompts import semantic_extraction_prompt
from src.induction.semantic import extract_semantic_records
from .test_config_data_contracts import config_for, valid_semantic_record, write_fixture_split
from src.induction.data import load_positive_samples


class RecordingClient:
    def __init__(self, output):
        self.output = output
        self.calls = 0

    def generate(self, **kwargs):
        self.calls += 1
        return SimpleNamespace(output=self.output)


class FailingClient:
    def generate(self, **kwargs):
        raise RuntimeError("provider unavailable")


def test_semantic_prompt_preserves_direction_without_predefined_modes(tmp_path):
    path = write_fixture_split(tmp_path / "train.json")
    sample = load_positive_samples(config_for(path))[0][0]
    system, user = semantic_extraction_prompt(sample)
    prompt = system + user
    assert "predefined reasoning mode" in prompt
    assert "mechanically replace every noun with an uppercase placeholder" in prompt
    assert "Appeal to Tradition" not in prompt
    assert sample["comment"] in prompt
    assert "What is the main premise or evidence?" in prompt
    assert "inferential bridge" in prompt
    assert "canonical_reasoning" in prompt
    assert "ambiguity_notes" not in prompt
    assert "The goal is NOT to summarize the comment" in prompt
    assert "What CANONICAL_REASONING must preserve" in prompt
    assert "Do not add reasoning that is absent from the original comment" in prompt
    assert "A harmful practice has persisted for a long time because those responsible avoid accountability" in prompt
    assert "Do not output explanations, markdown, or additional fields" in prompt


def test_semantic_prompt_preserves_persistence_interpretation_and_role_placeholders(tmp_path):
    path = write_fixture_split(tmp_path / "train.json")
    sample = load_positive_samples(config_for(path))[0][0]
    system, _ = semantic_extraction_prompt(sample)

    assert "legitimacy" in system
    assert "entrenched harm" in system
    assert "A harmful PRACTICE" in system
    assert "A SYSTEM has existed for a long time" in system
    assert "uppercase placeholder" in system
    assert "direction" in system


def test_resume_skips_existing_sample_key(tmp_path):
    path = write_fixture_split(tmp_path / "train.json")
    config = config_for(path)
    sample = load_positive_samples(config)[0][0]
    config.output_dir.mkdir(parents=True)
    (config.output_dir / "semantic_records.jsonl").write_text(
        json.dumps(valid_semantic_record(sample), ensure_ascii=False) + "\n", encoding="utf-8"
    )
    client = RecordingClient(valid_semantic_record(sample))
    records = extract_semantic_records(config, [sample], client, resume=True)
    assert len(records) == 1
    assert client.calls == 0


def test_resume_compacts_duplicate_sample_records(tmp_path):
    path = write_fixture_split(tmp_path / "train.json")
    config = config_for(path)
    sample = load_positive_samples(config)[0][0]
    record = valid_semantic_record(sample)
    config.output_dir.mkdir(parents=True)
    records_path = config.output_dir / "semantic_records.jsonl"
    records_path.write_text(
        json.dumps(record, ensure_ascii=False) + "\n" + json.dumps(record, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    client = RecordingClient(record)
    records = extract_semantic_records(config, [sample], client, resume=True)

    assert len(records) == 1
    assert client.calls == 0
    assert len(records_path.read_text(encoding="utf-8").splitlines()) == 1


def test_resume_compacts_failures_and_removes_completed_sample_failures(tmp_path):
    path = write_fixture_split(tmp_path / "train.json")
    config = config_for(path)
    sample = load_positive_samples(config)[0][0]
    record = valid_semantic_record(sample)
    config.output_dir.mkdir(parents=True)
    (config.output_dir / "semantic_records.jsonl").write_text(
        json.dumps(record, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    failure = {"sample_id": sample["sample_id"], "error": "old"}
    (config.output_dir / "semantic_failures.jsonl").write_text(
        json.dumps(failure) + "\n" + json.dumps(failure) + "\n", encoding="utf-8"
    )

    extract_semantic_records(config, [sample], RecordingClient(record), resume=True)

    assert (config.output_dir / "semantic_failures.jsonl").read_text(encoding="utf-8") == ""


def test_semantic_extraction_rejects_removed_fields(tmp_path):
    path = write_fixture_split(tmp_path / "train.json")
    config = config_for(path)
    sample = load_positive_samples(config)[0][0]
    record = valid_semantic_record(sample)
    record["ambiguity_notes"] = None

    with pytest.raises(RuntimeError, match="semantic extraction incomplete"):
        extract_semantic_records(config, [sample], RecordingClient(record))


def test_semantic_extraction_binds_model_ids_to_requested_sample(tmp_path):
    path = write_fixture_split(tmp_path / "train.json")
    config = config_for(path)
    sample = load_positive_samples(config)[0][0]
    wrong_ids = valid_semantic_record(sample)
    wrong_ids["sample_id"] = "999:wrong-comment"

    records = extract_semantic_records(config, [sample], RecordingClient(wrong_ids))

    assert records[0]["sample_id"] == sample["sample_id"]
    assert not (config.output_dir / "semantic_failures.jsonl").exists()


def test_missing_sample_is_not_replaced_by_placeholder(tmp_path):
    path = write_fixture_split(tmp_path / "train.json")
    config = config_for(path)
    sample = load_positive_samples(config)[0][0]
    with pytest.raises(RuntimeError, match="semantic extraction incomplete"):
        extract_semantic_records(config, [sample], FailingClient())
    failures = (config.output_dir / "semantic_failures.jsonl").read_text(encoding="utf-8")
    assert sample["sample_id"] in failures
