import json
from pathlib import Path

from src.data.loader import ModelInput
from src.io_utils import read_jsonl
from src.labels import FALLACIES
from src.llm.client import CallStats, GenerationResult
from src.single_llm import execute, run_zero_shot

from tests.test_runner import write_data


class RecordingClient:
    def __init__(self, labels):
        self.labels = iter(labels)
        self.calls = []

    def generate(self, **kwargs):
        self.calls.append(kwargs)
        return GenerationResult(
            output={"label": next(self.labels), "reason": "The required pattern is present."},
            stats=CallStats(
                stage="zero_shot",
                logical_calls=1,
                provider_calls=1,
                cache_hit=False,
                retries=0,
                prompt_tokens=20,
                completion_tokens=5,
                total_tokens=25,
                latency_seconds=0.1,
                model="fixture",
            ),
        )


def test_zero_shot_classification_makes_one_call_with_exact_label_space():
    client = RecordingClient(["Slippery Slope"])

    result = run_zero_shot(
        client,
        "classification",
        ModelInput("TITLE", "PARENT", "TARGET"),
        {"sample_id": "1:2", "split": "test"},
    )

    assert result.output["label"] == "Slippery Slope"
    assert len(client.calls) == 1
    call = client.calls[0]
    assert call["schema"]["properties"]["label"]["enum"] == list(FALLACIES)
    prompt_input = json.loads(call["user_prompt"])["input"]
    assert prompt_input == {"title": "TITLE", "parent_comment": "PARENT", "comment": "TARGET"}
    assert call["metadata"]["stage"] == "zero_shot"


def test_zero_shot_detection_is_binary_and_makes_one_call():
    client = RecordingClient(["Non-Fallacious"])

    result = run_zero_shot(
        client,
        "detection",
        ModelInput("TITLE", "", "TARGET"),
        {"sample_id": "1:1", "split": "test"},
    )

    assert result.output["label"] == "Non-Fallacious"
    assert len(client.calls) == 1
    assert client.calls[0]["schema"]["properties"]["label"]["enum"] == [
        "Non-Fallacious",
        "Fallacious",
    ]


def test_single_llm_execute_writes_metrics_with_one_call_per_sample(tmp_path):
    cfg = {
        "task": "detection",
        "data_dir": str(write_data(tmp_path)),
        "split": "test",
        "context": "paper",
        "model": {"name": "fixture", "provider": "mock", "max_attempts": 1},
        "output_root": str(tmp_path / "runs"),
        "cache_dir": str(tmp_path / "cache"),
    }
    client = RecordingClient(["Non-Fallacious", "Fallacious"])

    result = execute(cfg, output="single-test", client=client)

    run_dir = Path(cfg["output_root"]) / "single-test"
    assert result["status"] == "complete"
    assert result["accuracy"] == 1.0
    assert len(client.calls) == 2
    assert [call["metadata"]["sample_id"] for call in client.calls] == ["3:31", "3:32"]
    predictions = read_jsonl(run_dir / "predictions.jsonl")
    assert [row["prediction"] for row in predictions] == ["Non-Fallacious", "Fallacious"]
    samples = (run_dir / "samples.csv").read_text(encoding="utf-8")
    assert "logical_calls,provider_calls" in samples
    assert samples.count(",1,1,25,") == 2
