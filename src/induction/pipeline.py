import json
import os
from pathlib import Path

from src.induction.audit import audit_semantics
from src.induction.clustering import search_k
from src.induction.config import InductionConfig, load_config
from src.induction.data import load_positive_samples
from src.induction.embedding import embed_reasoning
from src.induction.induction import audit_clusters, induce_cluster_modes, induce_definition, merge_cluster_modes, _client
from src.induction.prompts import cluster_prompt_hashes, semantic_prompt_hash
from src.induction.reporting import write_run_manifest
from src.induction.semantic import extract_semantic_records
from src.io_utils import write_json


def _write_jsonl(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as stream:
        for row in rows:
            stream.write(json.dumps(row, ensure_ascii=False) + "\n")


def run_semantic_audit(config):
    return audit_semantics(config)


def run_embedding(config):
    return embed_reasoning(config)


def run_induction(config_or_path, resume=False):
    config = config_or_path if isinstance(config_or_path, InductionConfig) else load_config(config_or_path)
    config.output_dir.mkdir(parents=True, exist_ok=True)
    samples, stats = load_positive_samples(config)
    write_json(config.output_dir / "data_stats.json", stats)
    _write_jsonl(config.output_dir / "positive_samples.jsonl", samples)
    client = _client(config)
    extract_semantic_records(config, samples, client, resume=resume)
    semantic_gate = run_semantic_audit(config)
    if not semantic_gate["passed"]:
        raise RuntimeError("semantic audit has not passed")
    run_embedding(config)
    import numpy as np
    from src.io_utils import read_jsonl
    records = read_jsonl(config.output_dir / "semantic_records.jsonl")
    embeddings = np.load(config.output_dir / "canonical_embeddings.npy")
    clustering = search_k(config, embeddings, records)
    cluster_gate = audit_clusters(config, client=client)
    if not cluster_gate["passed"]:
        raise RuntimeError("cluster audit has not passed")
    modes = induce_cluster_modes(config, client=client)
    merge_cluster_modes(config, modes, client=client)
    write_run_manifest(config.output_dir, {
        "dataset": str(config.data_path), "label": config.label, "sample_count": len(samples),
        "seed": config.seed, "llm_model": os.environ.get(config.model_env, "configured-model"),
        "embedding_model": config.embedding_model, "embedding_normalized": config.embedding_normalize,
        "clustering_method": clustering["metrics"][0].get("method", config.clustering_method),
        "k_range": [config.k_min, config.k_max], "selected_k": clustering["selected_k"],
        "semantic_prompt_sha256": semantic_prompt_hash(), **cluster_prompt_hashes(),
    })
    induce_definition(config, client=client)
    return config.output_dir

