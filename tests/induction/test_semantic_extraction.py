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
    assert "predefined reasoning subtype" in prompt
    assert "Appeal to Tradition" not in prompt
    assert sample["comment"] in prompt


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


def test_missing_sample_is_not_replaced_by_placeholder(tmp_path):
    path = write_fixture_split(tmp_path / "train.json")
    config = config_for(path)
    sample = load_positive_samples(config)[0][0]
    with pytest.raises(RuntimeError, match="semantic extraction incomplete"):
        extract_semantic_records(config, [sample], FailingClient())
    failures = (config.output_dir / "semantic_failures.jsonl").read_text(encoding="utf-8")
    assert sample["sample_id"] in failures
