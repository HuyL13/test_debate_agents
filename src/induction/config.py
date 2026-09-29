from dataclasses import dataclass, field
from pathlib import Path

import yaml

from src.labels import FALLACIES
from src.runner import load_dotenv_file


@dataclass(frozen=True)
class InductionConfig:
    config_path: Path
    base_dir: Path
    data_path: Path
    label: str
    output_dir: Path
    seed: int = 42
    api_key_env: str = "OPENAI_API_KEY"
    base_url_env: str = "OPENAI_BASE_URL"
    model_env: str = "OPENAI_MODEL"
    llm_temperature: float = 0.0
    llm_max_retries: int = 5
    llm_max_completion_tokens: int = 4096
    llm_concurrency: int = 1
    use_parent_context: bool = False
    checkpoint_every: int = 10
    audit_random_n: int = 30
    embedding_model: str = "sentence-transformers/all-mpnet-base-v2"
    embedding_batch_size: int = 64
    embedding_normalize: bool = True
    k_min: int = 6
    k_max: int = 25
    clustering_metric: str = "cosine"
    clustering_method: str = "kmedoids"
    random_restarts: int = 10
    nearest_n: int = 5
    farthest_n: int = 5
    extra: dict = field(default_factory=dict, compare=False)


def _canonical_label(value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("data.label must be a non-empty string")
    value = value.strip()
    if value.lower() == "none":
        raise ValueError("none cannot be induced as a positive label")
    for label in FALLACIES:
        if label.lower() == value.lower():
            return label
    raise ValueError(f"Unknown fallacy label: {value}")


def _path(value, base_dir, field_name):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty path")
    path = Path(value)
    return (base_dir / path).resolve() if not path.is_absolute() else path.resolve()


def load_config_from_mapping(mapping, *, base_dir=None, config_path=None):
    if not isinstance(mapping, dict):
        raise ValueError("induction config must be a mapping")
    base_dir = Path(mapping.get("base_dir", base_dir or Path.cwd())).resolve()
    data = mapping.get("data") or {}
    llm = mapping.get("llm") or {}
    semantic = mapping.get("semantic") or {}
    embedding = mapping.get("embedding") or {}
    clustering = mapping.get("clustering") or {}
    audit = mapping.get("audit") or {}
    label = _canonical_label(data.get("label", "appeal to tradition"))
    k_min = int(clustering.get("k_min", 6))
    k_max = int(clustering.get("k_max", 25))
    if k_min < 2 or k_max < k_min:
        raise ValueError("clustering k range must satisfy 2 <= k_min <= k_max")
    metric = clustering.get("metric", "cosine")
    if metric != "cosine":
        raise ValueError("only cosine clustering is supported")
    return InductionConfig(
        config_path=Path(config_path or base_dir / "induction.yaml").resolve(),
        base_dir=base_dir,
        data_path=_path(data.get("path", "data/cocolofa/train.json"), base_dir, "data.path"),
        label=label,
        output_dir=_path(mapping.get("output_dir", "outputs/appeal_to_tradition_induction"), base_dir, "output_dir"),
        seed=int(mapping.get("seed", 42)),
        api_key_env=str(llm.get("api_key_env", "OPENAI_API_KEY")),
        base_url_env=str(llm.get("base_url_env", "OPENAI_BASE_URL")),
        model_env=str(llm.get("model_env", "OPENAI_MODEL")),
        llm_temperature=float(llm.get("temperature", 0.0)),
        llm_max_retries=int(llm.get("max_retries", 5)),
        llm_max_completion_tokens=int(llm.get("max_completion_tokens", 4096)),
        llm_concurrency=int(llm.get("concurrency", 1)),
        use_parent_context=bool(semantic.get("use_parent_context", False)),
        checkpoint_every=int(semantic.get("checkpoint_every", 10)),
        audit_random_n=int(semantic.get("audit_random_n", 30)),
        embedding_model=str(embedding.get("model", "sentence-transformers/all-mpnet-base-v2")),
        embedding_batch_size=int(embedding.get("batch_size", 64)),
        embedding_normalize=bool(embedding.get("normalize", True)),
        k_min=k_min,
        k_max=k_max,
        clustering_metric=metric,
        clustering_method=str(clustering.get("method", "kmedoids")),
        random_restarts=int(clustering.get("random_restarts", 10)),
        nearest_n=int(audit.get("nearest_n", 5)),
        farthest_n=int(audit.get("farthest_n", 5)),
        extra={"raw": mapping},
    )


def load_config(path):
    path = Path(path).resolve()
    for dotenv_path in (path.parent.parent / ".env", path.parent / ".env"):
        if dotenv_path.exists():
            load_dotenv_file(dotenv_path)
            break
    with path.open(encoding="utf-8") as stream:
        mapping = yaml.safe_load(stream) or {}
    mapping["base_dir"] = str(path.parent)
    return load_config_from_mapping(mapping, base_dir=path.parent, config_path=path)

