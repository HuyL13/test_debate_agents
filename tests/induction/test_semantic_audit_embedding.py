import json

import numpy as np
import pytest

from src.induction.audit import audit_semantics, check_representation_collapse
from src.induction.data import load_positive_samples
from src.induction.embedding import embed_records
from .test_config_data_contracts import config_for, valid_semantic_record, write_fixture_split


class RecordingSentenceTransformer:
    def __init__(self):
        self.seen_texts = None

    def encode(self, texts, **kwargs):
        self.seen_texts = list(texts)
        return np.asarray([[1.0, 0.0] if index == 0 else [0.0, 1.0] for index, _ in enumerate(texts)])


def _record_set(tmp_path):
    path = write_fixture_split(tmp_path / "train.json")
    config = config_for(path)
    sample = load_positive_samples(config)[0][0]
    record = valid_semantic_record(sample)
    config.output_dir.mkdir(parents=True)
    (config.output_dir / "positive_samples.jsonl").write_text(
        json.dumps(sample) + "\n", encoding="utf-8"
    )
    (config.output_dir / "semantic_records.jsonl").write_text(
        json.dumps(record) + "\n", encoding="utf-8"
    )
    return config, [record]


def test_semantic_audit_blocks_incomplete_records(tmp_path):
    path = write_fixture_split(tmp_path / "train.json")
    config = config_for(path)
    config.output_dir.mkdir(parents=True)
    (config.output_dir / "semantic_records.jsonl").write_text("", encoding="utf-8")
    result = audit_semantics(config)
    assert result["passed"] is False
    assert json.loads((config.output_dir / "semantic_gate.json").read_text())["passed"] is False


def test_representation_collapse_reports_exact_duplicates():
    records = [{"canonical_reasoning": "same reasoning"} for _ in range(40)]
    result = check_representation_collapse(records)
    assert result["unique_count"] == 1
    assert result["severe"] is True


def test_embedding_uses_only_canonical_reasoning(monkeypatch, tmp_path):
    config, records = _record_set(tmp_path)
    fake_model = RecordingSentenceTransformer()
    monkeypatch.setattr("src.induction.embedding.SentenceTransformer", fake_model)
    result = embed_records(records, config)
    assert fake_model.seen_texts == [records[0]["canonical_reasoning"]]
    assert result["input_field"] == "canonical_reasoning"
    assert result["normalized"] is True
    assert np.isclose(np.linalg.norm(result["embeddings"][0]), 1.0)


def test_embedding_refuses_failed_semantic_gate(tmp_path):
    config, _ = _record_set(tmp_path)
    (config.output_dir / "semantic_gate.json").write_text(json.dumps({"passed": False}), encoding="utf-8")
    from src.induction.embedding import embed_reasoning
    with pytest.raises(RuntimeError, match="semantic audit"):
        embed_reasoning(config)
