import json
from pathlib import Path

import numpy as np

from src.induction.audit import check_representation_collapse
from src.io_utils import read_jsonl, write_json


SentenceTransformer = None


def _load_model(config):
    global SentenceTransformer
    if SentenceTransformer is None:
        from sentence_transformers import SentenceTransformer as model_type
        SentenceTransformer = model_type
    if callable(SentenceTransformer):
        device = "cuda" if _cuda_available() else "cpu"
        return SentenceTransformer(config.embedding_model, device=device)
    return SentenceTransformer


def _cuda_available():
    try:
        import torch
        return bool(torch.cuda.is_available())
    except ImportError:
        return False


def embed_records(records, config, model=None):
    model = model or _load_model(config)
    texts = [record["canonical_reasoning"] for record in records]
    vectors = np.asarray(model.encode(texts, batch_size=config.embedding_batch_size,
                                      show_progress_bar=False, convert_to_numpy=True,
                                      normalize_embeddings=config.embedding_normalize), dtype=np.float32)
    if vectors.ndim != 2 or vectors.shape[0] != len(records):
        raise ValueError("embedding model returned an invalid matrix")
    if config.embedding_normalize:
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        vectors = vectors / np.maximum(norms, 1e-12)
    return {
        "embeddings": vectors,
        "model": config.embedding_model,
        "normalized": config.embedding_normalize,
        "input_field": "canonical_reasoning",
        "dimension": int(vectors.shape[1]),
        "collapse": check_representation_collapse(records, vectors),
    }


def embed_reasoning(config):
    output = Path(config.output_dir)
    gate_path = output / "semantic_gate.json"
    if not gate_path.exists() or not json.loads(gate_path.read_text(encoding="utf-8")).get("passed"):
        raise RuntimeError("semantic audit has not passed")
    records = read_jsonl(output / "semantic_records.jsonl")
    result = embed_records(records, config)
    np.save(output / "canonical_embeddings.npy", result["embeddings"])
    manifest = {key: value for key, value in result.items() if key not in {"embeddings", "collapse"}}
    manifest["collapse"] = result["collapse"]
    write_json(output / "embedding_manifest.json", manifest)
    return manifest

