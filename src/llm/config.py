import math
from dataclasses import dataclass
from urllib.parse import urlparse


@dataclass(frozen=True)
class ModelConfig:
    name: str
    provider: str = 'openai'
    base_url: str = 'https://api.openai.com/v1'
    api_key_env: str = 'OPENAI_API_KEY'
    temperature: float | None = 0.0
    max_completion_tokens: int = 1200
    timeout_seconds: float = 90.0
    max_attempts: int = 3
    backoff_seconds: float = 1.0
    structured_output: bool = True
    input_cost_per_million: float | None = None
    output_cost_per_million: float | None = None
    cached_input_cost_per_million: float | None = None

    def __post_init__(self):
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError('A model name is required')
        if self.provider not in ('openai', 'openai_compatible', 'mock'):
            raise ValueError('Unsupported provider')
        url = urlparse(self.base_url)
        if url.scheme not in ('https', 'http') or not url.hostname or url.query or url.fragment or url.username:
            raise ValueError('base_url must be a plain HTTP(S) endpoint with no credentials/query')
        if url.scheme == 'http' and url.hostname not in ('localhost', '127.0.0.1', '::1'):
            raise ValueError('Non-local endpoints require HTTPS')
        for name in ('max_completion_tokens', 'max_attempts'):
            if type(getattr(self, name)) is not int or getattr(self, name) < 1:
                raise ValueError(f'{name} must be a positive integer')
        if not 1 <= self.max_attempts <= 10:
            raise ValueError('max_attempts must be 1..10')
        for name in ('timeout_seconds', 'backoff_seconds', 'temperature', 'input_cost_per_million',
                     'output_cost_per_million', 'cached_input_cost_per_million'):
            value = getattr(self, name)
            if value is not None and (type(value) not in (int, float) or not math.isfinite(value) or value < 0):
                raise ValueError(f'Invalid {name}')
        if self.timeout_seconds <= 0 or (self.temperature is not None and self.temperature > 2):
            raise ValueError('Timeout must be positive and temperature must be 0..2 or null')
        if type(self.structured_output) is not bool:
            raise ValueError('structured_output must be boolean')
