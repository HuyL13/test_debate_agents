import json

from src.data.loader import Sample
from src.labels import FALLACIES
from src.llm.client import Client
from src.llm.config import ModelConfig
from src.property_graph.graph_io import load_graph
from src.property_graph.pipeline import (
    load_property_graph_config,
    run_pipeline,
    select_smoke_samples,
)


def samples():
    result = []
    for index, label in enumerate(FALLACIES, 1):
        result.append(Sample(
            f"{index}:{index}", index, str(index), "train", f"Title {index}",
            f"Target argument {index}", "Parent context", "Article", label, False,
        ))
    result.append(Sample(
        "99:99", 99, "99", "train", "None", "Not fallacious", "", "Article", "none", False,
    ))
    return result


def test_smoke_selection_is_train_positive_and_stratified():
    selected = select_smoke_samples(samples(), limit=8)
    assert len(selected) == 8
    assert all(sample.split == "train" and sample.fallacy != "none" for sample in selected)
    assert {sample.fallacy for sample in selected} == set(FALLACIES)


def test_config_resolves_env_without_storing_secret(monkeypatch):
    monkeypatch.setenv("NVIDIA_MODEL", "model-x")
    monkeypatch.setenv("NVIDIA_BASE_URL", "https://example.test/v1")
    monkeypatch.setenv("NVIDIA_API_KEY", "secret-value")
    config = load_property_graph_config("configs/property_graph.yaml")
    assert config["model"]["name"] == "model-x"
    assert config["model"]["base_url"] == "https://example.test/v1"
    assert "secret-value" not in json.dumps(config)


def test_mock_pipeline_writes_valid_graph_diff_and_indexes(tmp_path, monkeypatch):
    monkeypatch.setattr("src.property_graph.pipeline.load_split", lambda path: samples())
    config = load_property_graph_config("configs/property_graph.yaml")
    config["model"] = {
        "provider": "mock", "name": "mock", "base_url": "https://example.test/v1",
        "api_key_env": "NVIDIA_API_KEY", "temperature": 0.0,
        "max_completion_tokens": 1200, "timeout_seconds": 10,
        "max_attempts": 1, "backoff_seconds": 0.0, "structured_output": True,
    }
    output = tmp_path / "run"
    client = Client(
        ModelConfig(**config["model"]), tmp_path / "cache.sqlite", tmp_path / "audit.jsonl",
    )

    result = run_pipeline(config, "smoke", limit=8, output=output, client=client)

    assert result["extraction"]["completed"] == 8
    seed = load_graph(output / "seed_graph.json")
    evolved = load_graph(output / "fallacy_graph.json")
    assert len(evolved["nodes"]) > len(seed["nodes"])
    diff = json.loads((output / "graph_diff.json").read_text(encoding="utf-8"))
    assert diff["added_nodes"]
    assert (output / "graph_diff.md").exists()
    assert (output / "indexes" / "feature_to_nodes.json").exists()
    assert list((output / "graph_versions").glob("v*.json"))
