#!/usr/bin/env bash
set -euo pipefail

# Colab policy: this runner never installs or changes packages. In particular,
# do not add a pip/conda/apt step for torch; use a runtime that already has
# the required dependencies and report missing ones below.
PROJECT_DIR="${PROJECT_DIR:-/content/cocolofa_pard}"
CONFIG_PATH="${CONFIG_PATH:-configs/induction.yaml}"
HF_HOME="${HF_HOME:-${PROJECT_DIR}/.hf-cache}"

if [[ ! -d "${PROJECT_DIR}" ]]; then
  echo "Project directory not found: ${PROJECT_DIR}" >&2
  echo "Upload or clone the repository to /content/cocolofa_pard first." >&2
  exit 1
fi

cd "${PROJECT_DIR}"
export PYTHONPATH="${PROJECT_DIR}:${PYTHONPATH:-}"
export HF_HOME

if [[ -f ".env" ]]; then
  set -a
  source ".env"
  set +a
fi

if [[ ! -f "${CONFIG_PATH}" ]]; then
  echo "Config not found: ${PROJECT_DIR}/${CONFIG_PATH}" >&2
  exit 1
fi

: "${NVIDIA_API_KEY:?Set NVIDIA_API_KEY in Colab Secrets or .env}"
: "${NVIDIA_BASE_URL:?Set NVIDIA_BASE_URL in Colab Secrets or .env}"
: "${NVIDIA_MODEL:?Set NVIDIA_MODEL in Colab Secrets or .env}"

python - <<'PY'
import importlib

for name in ("numpy", "sklearn", "sentence_transformers", "yaml"):
    try:
        importlib.import_module(name)
    except ImportError as exc:
        raise SystemExit(
            f"Missing Colab dependency: {name}. Use a preconfigured runtime before running this script; no packages are installed here."
        ) from exc
PY

python -m scripts.run_induction --config "${CONFIG_PATH}" --resume

