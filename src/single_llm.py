import argparse
import json
import os
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path

from src.data.loader import load_split, select_task
from src.evaluate import score
from src.io_utils import append_jsonl, write_json
from src.labels import labels_for
from src.llm.client import Client
from src.llm.config import ModelConfig
from src.runner import load_config, validate_config
from src.trace import aggregate_call_stats, append_samples_csv, sample_trace_filename, write_sample_trace


FALLACY_DEFINITIONS = """Fallacy definitions:
- Appeal to Authority: treating an authority's opinion as sufficient proof of a claim.
- Appeal to Majority: treating popularity or widespread belief as proof that a claim is true or good.
- Appeal to Nature: treating something as good, right, or inevitable merely because it is natural.
- Appeal to Tradition: treating long-standing practice or belief as sufficient justification.
- Appeal to Worse Problems: dismissing or deprioritizing an issue only because a worse issue exists.
- False Dilemma: presenting limited alternatives as exhaustive when other possibilities exist.
- Hasty Generalization: drawing a broad conclusion from a small or unrepresentative sample.
- Slippery Slope: asserting an insufficiently supported chain from a small first step to a major outcome."""


def _schema(task):
    return {
        "type": "object",
        "properties": {
            "label": {"enum": list(labels_for(task))},
            "reason": {"type": "string", "minLength": 1, "maxLength": 600},
        },
        "required": ["label", "reason"],
        "additionalProperties": False,
    }


def _system_prompt(task):
    if task == "detection":
        instruction = """Determine whether COMMENT contains one of the eight logical fallacies below.
Use TITLE and PARENT_COMMENT only as context. Judge the reasoning in COMMENT itself.
Choose exactly Fallacious or Non-Fallacious. Do not use an unknown or borderline label."""
    else:
        instruction = """Determine which one of the eight logical fallacies appears in COMMENT.
Use TITLE and PARENT_COMMENT only as context. Judge the reasoning in COMMENT itself.
Choose exactly one supplied label."""
    return (
        "You are evaluating the CoCoLoFa logical-fallacy benchmark in a zero-shot setting.\n"
        + instruction
        + "\n"
        + FALLACY_DEFINITIONS
        + "\nReturn only the requested JSON object. Give a brief decision reason without a chain-of-thought."
    )


def run_zero_shot(client, task, model_input, metadata):
    labels_for(task)
    return client.generate(
        system_prompt=_system_prompt(task),
        user_prompt=json.dumps(
            {
                "task": task,
                "input": {
                    "title": model_input.title,
                    "parent_comment": model_input.parent_comment,
                    "comment": model_input.comment,
                },
            },
            ensure_ascii=False,
        ),
        schema=_schema(task),
        metadata={**metadata, "stage": "zero_shot"},
    )


def _run_dir(config, output):
    output_root = Path(config["output_root"]).resolve()
    if output:
        name = output
    else:
        model = config["model"]["name"].split("/")[-1]
        stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H%M%S")
        name = f"{config['task']}__{config['split']}__single-llm-zero-shot__{model}__{stamp}"
    run_dir = (output_root / name).resolve()
    if run_dir == output_root or output_root not in run_dir.parents:
        raise ValueError("Output name must stay inside output_root")
    return run_dir


def _prediction(trace):
    return {
        "sample_id": trace["sample"]["id"],
        "task": trace["sample"]["task"],
        "gold": trace["sample"]["gold"],
        "prediction": trace["result"]["prediction"],
        "status": "ok",
    }


def execute(config, *, limit=None, resume=False, output=None, client=None):
    config = validate_config(config)
    if limit is not None and (type(limit) is not int or limit < 1):
        raise ValueError("limit must be a positive integer")
    samples = select_task(
        load_split(Path(config["data_dir"]) / f"{config['split']}.json"), config["task"]
    )
    if limit:
        samples = samples[:limit]

    run_dir = _run_dir(config, output or config.get("output"))
    if run_dir.exists() and any(run_dir.iterdir()) and not resume:
        print(f"Overwriting existing output: {run_dir}", flush=True)
        shutil.rmtree(run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)

    manifest = {
        "task": config["task"],
        "split": config["split"],
        "context": config["context"],
        "method": "single-llm-zero-shot",
        "max_provider_calls_per_sample": 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "selection": {"sample_ids": [sample.sample_id for sample in samples]},
    }
    manifest_path = run_dir / "manifest.json"
    if resume and manifest_path.exists():
        saved = json.loads(manifest_path.read_text(encoding="utf-8"))
        keys = ("task", "split", "context", "method", "selection")
        if {key: saved[key] for key in keys} != {key: manifest[key] for key in keys}:
            raise ValueError("Resume manifest differs from requested config or selection")
    else:
        write_json(manifest_path, manifest)

    if client is None:
        model = {**config["model"], "max_attempts": 1}
        raw_debug = run_dir / "debug" / "raw_api.jsonl" if os.environ.get("TRACE_RAW_API") == "1" else None
        client = Client(
            ModelConfig(**model),
            Path(config["cache_dir"]) / "single_llm_responses.sqlite",
            run_dir / "audit" / "api_calls.jsonl",
            raw_debug_path=raw_debug,
        )

    predictions = []
    errors = []
    print(f"Run directory: {run_dir}", flush=True)
    print(f"Task: {config['task']} split={config['split']} samples={len(samples)} method=single-llm-zero-shot", flush=True)
    for index, sample in enumerate(samples, 1):
        trace_path = run_dir / "traces" / sample_trace_filename(sample.sample_id)
        if resume and trace_path.exists():
            import yaml

            trace = yaml.safe_load(trace_path.read_text(encoding="utf-8"))
            predictions.append(_prediction(trace))
            print(f"[{index}/{len(samples)}] {sample.sample_id} resume-skip", flush=True)
            continue
        model_input = sample.model_input(config["context"])
        started = time.monotonic()
        try:
            print(f"[{index}/{len(samples)}] {sample.sample_id} start", flush=True)
            generation = run_zero_shot(
                client,
                config["task"],
                model_input,
                {"sample_id": sample.sample_id, "split": config["split"]},
            )
            stats = aggregate_call_stats([generation], time.monotonic() - started)
            gold = sample.gold(config["task"])
            prediction = generation.output["label"]
            trace = {
                "sample": {
                    "id": sample.sample_id,
                    "article_id": sample.article_id,
                    "task": config["task"],
                    "split": config["split"],
                    "gold": gold,
                },
                "input": {
                    "title": model_input.title,
                    "parent": model_input.parent_comment,
                    "target": model_input.comment,
                },
                "zero_shot": generation.output,
                "result": {"prediction": prediction, "correct": prediction == gold},
                "stats": stats,
            }
            write_sample_trace(run_dir / "traces", trace)
            row = _prediction(trace)
            predictions.append(row)
            append_samples_csv(
                run_dir / "samples.csv",
                {
                    "sample_id": sample.sample_id,
                    "gold": gold,
                    "prediction": prediction,
                    "correct": str(prediction == gold).lower(),
                    "initial_candidates": "",
                    "conflict_count": 0,
                    "logical_calls": stats["logical_calls"],
                    "provider_calls": stats["provider_calls"],
                    "total_tokens": stats["total_tokens"],
                    "wall_time_seconds": stats["wall_time_seconds"],
                },
            )
            print(
                f"[{index}/{len(samples)}] {sample.sample_id} done prediction={prediction} gold={gold} "
                f"logical_calls={stats['logical_calls']} provider_calls={stats['provider_calls']} "
                f"tokens={stats['total_tokens']} seconds={stats['wall_time_seconds']:.2f}",
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
    metrics = (
        {"status": "incomplete", "metrics": None, "failed_samples": errors}
        if errors
        else {"status": "complete", **score(predictions)}
    )
    write_json(run_dir / "metrics.json", metrics)
    return metrics


def cli():
    parser = argparse.ArgumentParser(description="Run a one-call zero-shot CoCoLoFa baseline.")
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


if __name__ == "__main__":
    raise SystemExit(cli())
