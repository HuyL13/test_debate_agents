from pathlib import Path

from scripts.provider_smoke import (
    build_provider_config,
    extract_model_ids,
    get_provider_spec,
)


def test_extract_model_ids_from_openai_models_response():
    payload = {
        'data': [
            {'id': 'first-model'},
            {'id': ''},
            {'name': 'missing-id'},
            {'id': 'second-model'},
        ]
    }

    assert extract_model_ids(payload) == ['first-model', 'second-model']


def test_provider_spec_maps_nvidia_key_without_exposing_secret():
    spec = get_provider_spec('nvidia_3')

    assert spec.base_env == 'NVIDIA_BASE_URL'
    assert spec.key_env == 'NVIDIA_API_KEY_3'
    assert spec.model_env == 'NVIDIA_MODEL'
    assert spec.slug == 'nvidia-3'


def test_build_provider_config_overrides_only_runtime_model_fields(tmp_path):
    base_config = {
        'task': 'detection',
        'model': {
            'provider': 'gemini',
            'name': 'old-model',
            'base_url': 'https://old.invalid/v1',
            'api_key_env': 'OLD_KEY',
        },
        'output_dir': 'outputs/old',
        'cache_dir': 'cache/old',
    }

    configured = build_provider_config(
        base_config,
        'market',
        'market-model',
        tmp_path / 'outputs',
        tmp_path / 'cache',
    )

    assert configured['task'] == 'detection'
    assert configured['model'] == {
        'provider': 'openai_compatible',
        'name': 'market-model',
        'base_url': 'https://mkp-api.fptcloud.com/v1/',
        'api_key_env': 'MARKET_API_KEY',
    }
    assert configured['output_dir'] == str(tmp_path / 'outputs' / 'market')
    assert configured['cache_dir'] == str(tmp_path / 'cache' / 'market')
    assert base_config['model']['name'] == 'old-model'
