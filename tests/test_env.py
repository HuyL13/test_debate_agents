import os

import pytest

from src.runner import expand_env, load_dotenv_file


def test_dotenv_file_populates_missing_environment(tmp_path, monkeypatch):
    env_path = tmp_path / ".env"
    env_path.write_text("NVIDIA_API_KEY=abc123\nNVIDIA_MODEL=test-model\n", encoding="utf-8")
    monkeypatch.delenv("NVIDIA_API_KEY", raising=False)
    monkeypatch.setenv("NVIDIA_MODEL", "already-set")

    load_dotenv_file(env_path)

    assert os.environ["NVIDIA_API_KEY"] == "abc123"
    assert os.environ["NVIDIA_MODEL"] == "already-set"


def test_expand_env_rejects_missing_required_variable(monkeypatch):
    monkeypatch.delenv("NVIDIA_API_KEY", raising=False)

    with pytest.raises(ValueError, match="NVIDIA_API_KEY"):
        expand_env({"api_key_env": "NVIDIA_API_KEY"})
