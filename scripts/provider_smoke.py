"""Run one real ARS sample through OpenAI-compatible API providers.

Keys are read only from environment variables. The script never prints them.
"""

import argparse
import copy
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.io_utils import write_json
from src.runner import execute, load_config


@dataclass(frozen=True)
class ProviderSpec:
    slug: str
    base_env: str
    key_env: str
    model_env: str
    default_base_url: str


PROVIDER_SPECS = {
    'market': ProviderSpec(
        slug='market',
        base_env='MARKET_API_BASE',
        key_env='MARKET_API_KEY',
        model_env='MARKET_MODEL',
        default_base_url='https://mkp-api.fptcloud.com/v1/',
    ),
    '9router': ProviderSpec(
        slug='9router',
        base_env='9ROUTER_API_BASE',
        key_env='9ROUTER_API_KEY',
        model_env='ROUTER_MODEL',
        default_base_url='http://localhost:20128/v1',
    ),
    'minimax': ProviderSpec(
        slug='minimax',
        base_env='MINIMAX_BASE_URL',
        key_env='MINIMAX_API_KEY',
        model_env='MINIMAX_MODEL',
        default_base_url='https://api.minimax.io/v1',
    ),
}


def get_provider_spec(name):
    if name in PROVIDER_SPECS:
        return PROVIDER_SPECS[name]

    if name.startswith('nvidia_'):
        try:
            index = int(name.removeprefix('nvidia_'))
        except ValueError as exc:
            raise ValueError(f'Invalid NVIDIA provider name: {name}') from exc
        if not 1 <= index <= 9:
            raise ValueError('NVIDIA key index must be 1..9')
        return ProviderSpec(
            slug=f'nvidia-{index}',
            base_env='NVIDIA_BASE_URL',
            key_env=f'NVIDIA_API_KEY_{index}',
            model_env='NVIDIA_MODEL',
            default_base_url='https://integrate.api.nvidia.com/v1',
        )

    raise ValueError(
        f'Unknown provider {name!r}; use market, 9router, minimax, or nvidia_1..nvidia_9'
    )


def extract_model_ids(payload):
    data = payload.get('data') if isinstance(payload, dict) else None
    if not isinstance(data, list):
        return []
    result = []
    for item in data:
        model_id = item.get('id') if isinstance(item, dict) else None
        if isinstance(model_id, str) and model_id and model_id not in result:
            result.append(model_id)
    return result


def discover_model(spec, base_url, key, timeout=20):
    request = Request(
        base_url.rstrip('/') + '/models',
        headers={
            'Authorization': 'Bearer ' + key,
            'Accept': 'application/json',
        },
        method='GET',
    )
    with urlopen(request, timeout=timeout) as response:
        payload = json.loads(response.read().decode('utf-8'))
    models = extract_model_ids(payload)
    if not models:
        raise ValueError('Provider returned no model IDs from /models')
    return models[0]


def resolve_model_name(base_config, spec, base_url, key, model_override=None, discover=discover_model):
    model_name = model_override or os.environ.get(spec.model_env)
    configured_model = base_config.get('model', {}).get('name')
    if not model_name and configured_model not in (None, '', 'SET_MODEL_SNAPSHOT'):
        model_name = configured_model
    if model_name:
        return model_name
    return discover(spec, base_url, key)


def build_provider_config(base_config, provider_name, model_name, output_root, cache_root):
    spec = get_provider_spec(provider_name)
    configured = copy.deepcopy(base_config)
    model = configured['model']
    model.update(
        provider='openai_compatible',
        name=model_name,
        base_url=os.environ.get(spec.base_env, spec.default_base_url),
        api_key_env=spec.key_env,
    )
    configured['output_dir'] = str(Path(output_root) / spec.slug)
    configured['cache_dir'] = str(Path(cache_root) / spec.slug)
    return configured


def run_provider(base_config, provider_name, limit, output_root, cache_root, model_override=None):
    spec = get_provider_spec(provider_name)
    key = os.environ.get(spec.key_env)
    if not key:
        return {
            'provider': provider_name,
            'status': 'missing_key',
            'key_env': spec.key_env,
        }

    base_url = os.environ.get(spec.base_env, spec.default_base_url)
    try:
        model_name = resolve_model_name(
            base_config,
            spec,
            base_url,
            key,
            model_override,
        )
        config = build_provider_config(
            base_config,
            provider_name,
            model_name,
            output_root,
            cache_root,
        )
        summary = execute(config, limit=limit)
        return {
            'provider': provider_name,
            'model': model_name,
            'status': summary.get('status'),
            'output_dir': config['output_dir'],
            'api_calls': summary.get('usage', {}).get('api_calls'),
            'cache_hits': summary.get('usage', {}).get('cache_hits'),
            'synthetic': summary.get('synthetic'),
        }
    except Exception as exc:
        return {
            'provider': provider_name,
            'model': model_name,
            'status': 'error',
            'error': f'{type(exc).__name__}: {exc}',
        }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', default='configs/detection.ars_no_debate.yaml')
    parser.add_argument('--providers', required=True,
                        help='Comma-separated: market,9router,minimax,nvidia_1..nvidia_9')
    parser.add_argument('--limit', type=int, default=1)
    parser.add_argument('--model', help='Use one model name for every provider')
    parser.add_argument('--output-root', default='outputs/provider-smoke')
    parser.add_argument('--cache-root', default='cache/provider-smoke')
    args = parser.parse_args()

    if args.limit < 1:
        parser.error('--limit must be positive')
    base_config = load_config(args.config)
    provider_names = [name.strip() for name in args.providers.split(',') if name.strip()]
    if not provider_names:
        parser.error('--providers must not be empty')

    results = []
    for provider_name in provider_names:
        result = run_provider(
            base_config,
            provider_name,
            args.limit,
            args.output_root,
            args.cache_root,
            args.model,
        )
        results.append(result)
        print(json.dumps(result, ensure_ascii=False), flush=True)

    output_root = Path(args.output_root)
    output_root.mkdir(parents=True, exist_ok=True)
    write_json(output_root / 'summary.json', {'providers': results})
    return 0 if all(result['status'] == 'complete' for result in results) else 1


if __name__ == '__main__':
    raise SystemExit(main())
