import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import yaml

from src.data.loader import load_split, select_task
from src.engine import Engine
from src.evaluate import score
from src.io_utils import append_jsonl, read_jsonl, write_json
from src.labels import labels_for
from src.llm.client import Client
from src.llm.config import ModelConfig
from src.trace import append_samples_csv, build_sample_trace, sample_trace_filename, write_sample_trace


CONFIG_KEYS = {"task", "data_dir", "split", "context", "model", "output_root", "cache_dir"}


def load_dotenv_file(path=".env"):
    path = Path(path)
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def expand_env(model):
    result = dict(model)
    for target, env_key in (("name", "name_env"), ("base_url", "base_url_env"), ("api_key", "api_key_env")):
        if env_key in result:
            env_name = result[env_key]
            value = os.environ.get(env_name)
            if not value:
                raise ValueError(f"Missing required environment variable: {env_name}")
            if target != "api_key":
                result[target] = value
    result.pop("name_env", None)
    result.pop("base_url_env", None)
    return result


def validate_config(config):
    if not isinstance(config, dict) or set(config) - (CONFIG_KEYS | {"output"}):
        raise ValueError(f"Config keys must be: {sorted(CONFIG_KEYS)}")
    labels_for(config["task"])
    if config["split"] not in ("train", "dev", "test") or config["context"] not in ("paper", "article", "comment_only"):
        raise ValueError("Unknown split or context")
    for key in ("data_dir", "output_root", "cache_dir"):
        if not isinstance(config.get(key), str) or not config[key]:
            raise ValueError(f"{key} must be a path string")
    if not isinstance(config.get("model"), dict):
        raise ValueError("model must be a mapping")
    model = expand_env(config["model"])
    ModelConfig(**model)
    return {**config, "model": model}


def load_config(path):
    load_dotenv_file(Path(path).resolve().parent.parent / ".env")
    config = validate_config(yaml.safe_load(Path(path).read_text(encoding="utf-8")))
    base = Path(path).resolve().parent.parent
    for key in ("data_dir", "output_root", "cache_dir"):
        value = Path(config[key])
        config[key] = str(value if value.is_absolute() else (base / value).resolve())
    return config


def _run_name(config, output=None):
    if output or config.get("output"):
        return output or config["output"]
    model = config["model"]["name"].split("/")[-1]
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H%M%S")
    return f"{config['task']}__{config['split']}__conflict-guided__{model}__{stamp}"


def _prediction_row(trace):
    sample = trace["sample"]
    return {
        "sample_id": sample["id"],
        "task": sample["task"],
        "gold": sample["gold"],
        "prediction": trace["arbiter"]["prediction"],
        "status": "ok",
    }


def _log_json(label, value):
    print(f"{label}: {json.dumps(value, ensure_ascii=False, sort_keys=True)}", flush=True)


def _shorten(text, limit=600):
    text = " ".join(str(text).split())
    return text if len(text) <= limit else text[: limit - 3] + "..."


def execute(config, *, limit=None, resume=False, output=None):
    config = validate_config(config)
    if limit is not None and (type(limit) is not int or limit < 1):
        raise ValueError("limit must be a positive integer")
    samples = select_task(load_split(Path(config["data_dir"]) / f"{config['split']}.json"), config["task"])
    if limit:
        samples = samples[:limit]
    run_dir = Path(config["output_root"]) / _run_name(config, output)
    if run_dir.exists() and any(run_dir.iterdir()) and not resume:
        raise ValueError("Output exists; use --resume or choose --output")
    run_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "task": config["task"],
        "split": config["split"],
        "context": config["context"],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "selection": {"sample_ids": [sample.sample_id for sample in samples]},
    }
    manifest_path = run_dir / "manifest.json"
    if resume and manifest_path.exists():
        saved = json.loads(manifest_path.read_text(encoding="utf-8"))
        comparable = {key: saved[key] for key in ("task", "split", "context", "selection")}
        expected = {key: manifest[key] for key in ("task", "split", "context", "selection")}
        if comparable != expected:
            raise ValueError("Resume manifest differs from requested config or selection")
    else:
        write_json(manifest_path, manifest)
    raw_debug_path = run_dir / "debug" / "raw_api.jsonl" if os.environ.get("TRACE_RAW_API") == "1" else None
    client = Client(
        ModelConfig(**config["model"]),
        Path(config["cache_dir"]) / "responses.sqlite",
        run_dir / "audit" / "api_calls.jsonl",
        raw_debug_path=raw_debug_path,
    )
    engine = Engine(client, task=config["task"])
    predictions = []
    errors = []
    print(f"Run directory: {run_dir}", flush=True)
    print(f"Task: {config['task']} split={config['split']} samples={len(samples)}", flush=True)
    for index, sample in enumerate(samples, 1):
        trace_path = run_dir / "traces" / sample_trace_filename(sample.sample_id)
        if resume and trace_path.exists():
            trace = yaml.safe_load(trace_path.read_text(encoding="utf-8"))
            predictions.append(_prediction_row(trace))
            print(f"[{index}/{len(samples)}] {sample.sample_id} resume-skip", flush=True)
            continue
        model_input = sample.model_input(config["context"])
        try:
            print(f"[{index}/{len(samples)}] {sample.sample_id} start", flush=True)
            print(f"TARGET: {_shorten(model_input.comment)}", flush=True)
            result = engine.run(model_input, {"sample_id": sample.sample_id, "split": config["split"]})
            trace = build_sample_trace(
                sample={
                    "id": sample.sample_id,
                    "article_id": sample.article_id,
                    "task": config["task"],
                    "split": config["split"],
                    "gold": sample.gold(config["task"]),
                },
                model_input={
                    "title": model_input.title,
                    "parent": model_input.parent_comment,
                    "target": model_input.comment,
                },
                initial_analysis=result["initial_analysis"],
                conflicts=result["conflicts"],
                arbiter=result["arbiter"],
                stats=result["stats"],
            )
            write_sample_trace(run_dir / "traces", trace)
            row = _prediction_row(trace)
            predictions.append(row)
            append_samples_csv(run_dir / "samples.csv", {
                "sample_id": row["sample_id"],
                "gold": row["gold"],
                "prediction": row["prediction"],
                "correct": str(row["gold"] == row["prediction"]).lower(),
                "initial_candidates": "|".join(str(result["initial_analysis"][role]["candidate"]) for role in ("scheme", "enthymeme", "critical")),
                "conflict_count": len(result["conflicts"]),
                "logical_calls": result["stats"]["logical_calls"],
                "provider_calls": result["stats"]["provider_calls"],
                "total_tokens": result["stats"]["total_tokens"],
                "wall_time_seconds": result["stats"]["wall_time_seconds"],
            })
            for role in ("scheme", "enthymeme", "critical"):
                _log_json(f"  {role}", result["initial_analysis"][role])
            if result["conflicts"]:
                for conflict in result["conflicts"]:
                    _log_json("  conflict", conflict)
            else:
                print("  conflicts: none", flush=True)
            _log_json("  arbiter", result["arbiter"])
            print(
                f"[{index}/{len(samples)}] {sample.sample_id} done "
                f"prediction={row['prediction']} "
                f"calls={result['stats']['provider_calls']} "
                f"tokens={result['stats']['total_tokens']} "
                f"seconds={result['stats']['wall_time_seconds']:.2f}",
                flush=True,
            )
        except Exception as exc:
            errors.append({"sample_id": sample.sample_id, "error": f"{type(exc).__name__}: {exc}"})
            print(f"[{index}/{len(samples)}] {sample.sample_id} error {type(exc).__name__}: {exc}", flush=True)
            break
    predictions_path = run_dir / "predictions.jsonl"
    if predictions_path.exists():
        predictions_path.unlink()
    for row in predictions:
        append_jsonl(predictions_path, row)
    if errors:
        metrics = {"status": "incomplete", "metrics": None, "failed_samples": errors}
    else:
        metrics = {"status": "complete", **score(predictions)}
    write_json(run_dir / "metrics.json", metrics)
    return metrics


def evaluate_run(path):
    return score(read_jsonl(path))


def freeze(config, path):
    config = validate_config(config)
    path = Path(path)
    if path.exists():
        raise ValueError("Frozen file exists")
    write_json(path, {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "task": config["task"],
        "split": config["split"],
        "context": config["context"],
        "model": config["model"],
    })
    return {"experiment": {"fingerprint": path.stem}}


def cli():
    parser = argparse.ArgumentParser(description="Run the conflict-guided CoCoLoFa flow.")
    parser.add_argument("--config", required=True)
    parser.add_argument("--split", choices=("dev", "test"))
    parser.add_argument("--limit", type=int)
    parser.add_argument("--output")
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    config = load_config(args.config)
    if args.split:
        config["split"] = args.split
    result = execute(config, limit=args.limit, resume=args.resume, output=args.output)
    print(json.dumps(result, indent=2))
    return 0 if result["status"] == "complete" else 1
