"""Orchestration and CLI for property-graph induction."""

import argparse
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import yaml

from src.data.loader import load_split, select_task
from src.io_utils import digest, read_jsonl, write_json
from src.llm.client import Client
from src.llm.config import ModelConfig
from src.property_graph.extraction import extract_samples
from src.property_graph.graph_io import load_graph, save_graph
from src.property_graph.indexing import build_indexes, save_indexes
from src.property_graph.induction import induce_cross_label, induce_within_label
from src.property_graph.normalization import normalize_signature
from src.property_graph.reporting import (
    diff_graphs,
    render_graph_diff,
    render_induction_audit,
)
from src.property_graph.seed import build_seed_graph, load_definitions
from src.runner import expand_env, load_dotenv_file


REQUIRED_CONFIG_KEYS = {
    "data_dir", "definitions", "output_root", "cache_dir", "prompt_version",
    "model", "induction", "retrieval",
}


def load_property_graph_config(path):
    path = Path(path).resolve()
    load_dotenv_file(path.parent.parent / ".env")
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or set(raw) != REQUIRED_CONFIG_KEYS:
        raise ValueError(f"property graph config keys must be {sorted(REQUIRED_CONFIG_KEYS)}")
    config = dict(raw)
    config["model"] = expand_env(config["model"])
    ModelConfig(**config["model"])
    for key in ("data_dir", "definitions", "output_root", "cache_dir"):
        value = Path(config[key])
        config[key] = str(value if value.is_absolute() else (path.parent.parent / value).resolve())
    return config


def select_smoke_samples(samples, limit):
    if type(limit) is not int or limit < 1:
        raise ValueError("limit must be a positive integer")
    positives = [
        sample for sample in samples
        if sample.split == "train" and sample.fallacy != "none"
    ]
    by_label = {}
    for sample in positives:
        by_label.setdefault(sample.fallacy, []).append(sample)
    for values in by_label.values():
        values.sort(key=lambda item: item.sample_id)

    selected = []
    labels = sorted(by_label)
    while len(selected) < limit:
        progressed = False
        for label in labels:
            if by_label[label] and len(selected) < limit:
                selected.append(by_label[label].pop(0))
                progressed = True
        if not progressed:
            break
    if len(selected) < limit:
        raise ValueError(f"only {len(selected)} positive train samples are available")
    return selected


def _git_commit():
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"], check=True, capture_output=True, text=True,
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return "unknown"


def _next_version(directory):
    directory.mkdir(parents=True, exist_ok=True)
    numbers = []
    for path in directory.glob("v*.json"):
        try:
            numbers.append(int(path.stem[1:]))
        except ValueError:
            continue
    return f"v{max(numbers, default=0) + 1:03d}"


def _build_client(config, output):
    return Client(
        ModelConfig(**config["model"]),
        Path(config["cache_dir"]) / "responses.sqlite",
        output / "audit" / "api_calls.jsonl",
        raw_debug_path=(
            output / "debug" / "raw_api.jsonl"
            if os.environ.get("TRACE_RAW_API") == "1" else None
        ),
    )


def _provider_audit_summary(path):
    path = Path(path)
    events = read_jsonl(path) if path.exists() else []
    return {
        "provider_calls": sum(not event.get("cache_hit", False) for event in events),
        "cache_hits": sum(event.get("cache_hit", False) for event in events),
        "retry_events": sum((event.get("attempt") or 1) > 1 for event in events),
        "valid_responses": sum(event.get("valid", False) for event in events),
        "invalid_responses": sum(not event.get("valid", False) for event in events),
        "total_tokens": sum((event.get("usage") or {}).get("total_tokens", 0) for event in events),
        "latency_seconds": sum(event.get("latency_seconds", 0.0) for event in events),
    }


def run_pipeline(config, command, *, limit=None, output=None, resume=False, client=None):
    if command == "validate":
        graph = load_graph(output)
        return {"status": "valid", "nodes": len(graph["nodes"]), "edges": len(graph["edges"])}
    if command != "smoke":
        raise ValueError("run_pipeline currently orchestrates smoke or validate")

    output = Path(output or config["output_root"]).resolve()
    output.mkdir(parents=True, exist_ok=True)
    signatures_path = output / "train_signatures.jsonl"
    failures_path = output / "extraction_failures.jsonl"
    if not resume:
        for path in (signatures_path, failures_path):
            if path.exists():
                path.unlink()

    all_samples = select_task(load_split(Path(config["data_dir"]) / "train.json"), "classification")
    samples = select_smoke_samples(all_samples, limit or 8)
    version_dir = output / "graph_versions"
    version = _next_version(version_dir)
    meta = {
        "schema_version": "1.0",
        "graph_version": version,
        "dataset": "CoCoLoFa",
        "task": "classification",
        "train_samples": len(samples),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "git_commit": _git_commit(),
        "config_hash": digest(config),
        "prompt_version": config["prompt_version"],
        "train_selection_hash": digest([sample.sample_id for sample in samples]),
    }
    seed = build_seed_graph(load_definitions(config["definitions"]), meta)
    save_graph(seed, output / "seed_graph.json")

    client = client or _build_client(config, output)
    extraction = extract_samples(
        samples,
        client,
        signatures_path,
        failures_path,
        prompt_version=config["prompt_version"],
        resume=resume,
    )
    records = read_jsonl(signatures_path) if signatures_path.exists() else []
    for record in records:
        record["features"] = normalize_signature(record["raw_signature"])
    within, within_audit = induce_within_label(seed, records, config["induction"])
    evolved, cross_audit = induce_cross_label(within, records, config["induction"])
    save_graph(evolved, output / "fallacy_graph.json")
    save_graph(evolved, version_dir / f"{version}.json")

    indexes = build_indexes(evolved)
    save_indexes(indexes, output / "indexes")
    audit = {"within_label": within_audit, "cross_label": cross_audit}
    graph_diff = diff_graphs(seed, evolved, audit=within_audit)
    write_json(output / "graph_diff.json", graph_diff)
    (output / "graph_diff.md").write_text(render_graph_diff(graph_diff), encoding="utf-8")
    (output / "graph_induction_report.md").write_text(
        render_induction_audit(audit), encoding="utf-8",
    )
    manifest = {
        "status": "complete" if extraction["failed"] == 0 else "partial",
        "sample_ids": [sample.sample_id for sample in samples],
        "label_coverage": sorted({sample.fallacy for sample in samples}),
        "graph_version": version,
        "extraction": extraction,
        "provider_audit": _provider_audit_summary(output / "audit" / "api_calls.jsonl"),
        "seed": {"nodes": len(seed["nodes"]), "edges": len(seed["edges"])},
        "evolved": {"nodes": len(evolved["nodes"]), "edges": len(evolved["edges"])},
    }
    write_json(output / "manifest.json", manifest)
    return manifest


def build_parser():
    parser = argparse.ArgumentParser(description="Induce and inspect a CoCoLoFa property graph.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    smoke = subparsers.add_parser("smoke")
    smoke.add_argument("--config", required=True)
    smoke.add_argument("--limit", type=int, default=8)
    smoke.add_argument("--output", required=True)
    smoke.add_argument("--resume", action="store_true")
    validate = subparsers.add_parser("validate")
    validate.add_argument("--graph", required=True)
    return parser


def cli(argv=None):
    args = build_parser().parse_args(argv)
    if args.command == "validate":
        result = run_pipeline({}, "validate", output=args.graph)
    else:
        result = run_pipeline(
            load_property_graph_config(args.config),
            "smoke",
            limit=args.limit,
            output=args.output,
            resume=args.resume,
        )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") not in {"partial"} else 1


if __name__ == "__main__":
    raise SystemExit(cli())

