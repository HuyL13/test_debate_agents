import json
from pathlib import Path

import yaml

from src.io_utils import read_jsonl
from src.runner import execute, load_config


def write_data(tmp_path):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    for split, aid in [("train", 1), ("dev", 2), ("test", 3)]:
        articles = [
            {
                "id": aid,
                "title": "Election",
                "content": "<p>News</p>",
                "comments": [
                    {
                        "id": f"{aid}1",
                        "news_id": aid,
                        "fallacy": "none",
                        "respond_to": "",
                        "comment": "I think this election is about good and evil.",
                    },
                    {
                        "id": f"{aid}2",
                        "news_id": aid,
                        "fallacy": "slippery slope",
                        "respond_to": f"{aid}1",
                        "comment": "This rhetoric leads to action, then things go from bad to worse.",
                    },
                ],
            }
        ]
        (data_dir / f"{split}.json").write_text(json.dumps(articles), encoding="utf-8")
    return data_dir


def config(tmp_path):
    return {
        "task": "detection",
        "data_dir": str(write_data(tmp_path)),
        "split": "dev",
        "context": "paper",
        "model": {"name": "fixture", "provider": "mock"},
        "output_root": str(tmp_path / "runs"),
        "cache_dir": str(tmp_path / "cache"),
        "output": "smoke",
    }


def test_runner_writes_yaml_traces_samples_csv_and_audit(tmp_path):
    cfg = config(tmp_path)

    result = execute(cfg, limit=1)

    run = Path(cfg["output_root"]) / "smoke"
    assert result["status"] == "complete"
    assert (run / "manifest.json").exists()
    assert (run / "metrics.json").exists()
    assert (run / "samples.csv").exists()
    traces = list((run / "traces").glob("article-*__comment-*.yaml"))
    assert len(traces) == 1
    trace = yaml.safe_load(traces[0].read_text(encoding="utf-8"))
    assert trace["stats"]["logical_calls"] >= 4
    assert (run / "audit" / "api_calls.jsonl").exists()
    assert not (run / "debug").exists()
    assert read_jsonl(run / "predictions.jsonl")[0]["sample_id"] == "2:21"


def test_runner_prints_progress_while_samples_run(tmp_path, capsys):
    cfg = config(tmp_path)

    execute(cfg, limit=1)

    out = capsys.readouterr().out
    assert "Run directory:" in out
    assert "[1/1] 2:21 start" in out
    assert "TARGET: I think this election is about good and evil." in out
    assert "scheme:" in out
    assert "enthymeme:" in out
    assert "critical:" in out
    assert "arbiter:" in out
    assert "[1/1] 2:21 done" in out


def test_resume_keeps_manifest_and_does_not_duplicate_completed_sample(tmp_path):
    cfg = config(tmp_path)
    execute(cfg, limit=1)
    run = Path(cfg["output_root"]) / "smoke"
    manifest_before = (run / "manifest.json").read_text(encoding="utf-8")
    samples_before = (run / "samples.csv").read_text(encoding="utf-8")

    execute(cfg, limit=1, resume=True)

    assert (run / "manifest.json").read_text(encoding="utf-8") == manifest_before
    assert (run / "samples.csv").read_text(encoding="utf-8") == samples_before
    assert len(read_jsonl(run / "predictions.jsonl")) == 1


def test_load_config_accepts_new_minimal_shape(tmp_path):
    data_dir = write_data(tmp_path)
    path = tmp_path / "config.yaml"
    path.write_text(
        f"""
task: detection
data_dir: {data_dir.as_posix()}
split: dev
context: paper
model:
  provider: mock
  name: fixture
output_root: {tmp_path.as_posix()}/runs
cache_dir: {tmp_path.as_posix()}/cache
""",
        encoding="utf-8",
    )

    loaded = load_config(path)

    assert loaded["task"] == "detection"
    assert loaded["output_root"].endswith("runs")
