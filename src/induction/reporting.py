import copy
from pathlib import Path

from src.io_utils import write_json


def _without_secrets(value):
    if isinstance(value, dict):
        return {key: _without_secrets(item) for key, item in value.items()
                if not any(token in key.lower() for token in ("api_key", "secret", "password", "token"))}
    if isinstance(value, list):
        return [_without_secrets(item) for item in value]
    return value


def write_run_manifest(output_dir, manifest_data):
    path = Path(output_dir) / "run_manifest.json"
    safe = _without_secrets(copy.deepcopy(manifest_data))
    write_json(path, safe)
    return path

