import importlib
import json

import pytest

from src.induction.config import load_config_from_mapping
from src.induction.reporting import write_run_manifest
from src.induction.pipeline import run_induction


def config_for_output(tmp_path):
    return load_config_from_mapping({
        "base_dir": str(tmp_path),
        "data": {"path": "train.json", "label": "Appeal to Tradition"},
        "output_dir": "output",
    })


def test_pipeline_stops_before_embedding_when_semantic_audit_fails(monkeypatch, tmp_path):
    config = config_for_output(tmp_path)
    calls = []
    monkeypatch.setattr("src.induction.pipeline.load_positive_samples", lambda *_: ([{"sample_id": "1:c1"}], {"positive_sample_count": 1}))
    monkeypatch.setattr("src.induction.pipeline._client", lambda *_: object())
    monkeypatch.setattr("src.induction.pipeline.extract_semantic_records", lambda *args, **kwargs: [])
    monkeypatch.setattr("src.induction.pipeline.run_semantic_audit", lambda *_: {"passed": False})
    monkeypatch.setattr("src.induction.pipeline.run_embedding", lambda *_: calls.append("embedding"))
    with pytest.raises(RuntimeError, match="semantic audit"):
        run_induction(config)
    assert calls == []


def test_manifest_excludes_api_key(tmp_path):
    path = write_run_manifest(tmp_path, {"api_key": "secret", "llm_model": "model"})
    assert "secret" not in path.read_text(encoding="utf-8")
    assert json.loads(path.read_text(encoding="utf-8"))["llm_model"] == "model"


def test_all_stage_modules_import():
    for name in (
        "semantic_extract", "audit_semantics", "embed_reasoning", "cluster_search",
        "audit_clusters", "induce_cluster_modes", "induce_definition", "run_induction",
    ):
        importlib.import_module("scripts." + name)


def test_property_graph_is_not_a_runtime_entry_point():
    text = open("pyproject.toml", encoding="utf-8").read()
    assert "property_graph" not in text
