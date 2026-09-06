import json
import os
from urllib.request import Request, urlopen


class OpenAITransport:
    """Chat Completions only. No tool definitions or retrieval endpoints exist here."""
    def __init__(self, config):
        self.config = config

    def complete(self, payload):
        key = os.environ.get(self.config.api_key_env)
        if not key:
            raise RuntimeError(f'Set {self.config.api_key_env} in the environment before an API run')
        request = Request(self.config.base_url.rstrip('/') + '/chat/completions',
                          data=json.dumps(payload, allow_nan=False).encode('utf-8'),
                          headers={'Authorization': 'Bearer ' + key, 'Content-Type': 'application/json'},
                          method='POST')
        with urlopen(request, timeout=self.config.timeout_seconds) as response:
            body = response.read().decode('utf-8')
        try:
            parsed = json.loads(body)
        except json.JSONDecodeError:
            return {'unparsed_body': body}
        if not isinstance(parsed, dict):
            return {'unparsed_body': body}
        return parsed
