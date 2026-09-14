import json
import time
from copy import deepcopy
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError

from src.io_utils import append_jsonl, digest
from src.llm.cache import Cache
from src.llm.config import ModelConfig
from src.llm.mock import MockTransport
from src.llm.openai_client import OpenAITransport
from src.schemas import validate_output


@dataclass(frozen=True)
class CallStats:
    stage: str
    logical_calls: int
    provider_calls: int
    cache_hit: bool
    retries: int
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    latency_seconds: float
    model: str


@dataclass(frozen=True)
class GenerationResult:
    output: dict
    stats: CallStats


def _usage(response):
    usage = response.get("usage") or {}
    return {
        "prompt_tokens": usage.get("prompt_tokens", 0) if isinstance(usage.get("prompt_tokens", 0), int) else 0,
        "completion_tokens": usage.get("completion_tokens", 0) if isinstance(usage.get("completion_tokens", 0), int) else 0,
        "total_tokens": usage.get("total_tokens", 0) if isinstance(usage.get("total_tokens", 0), int) else 0,
    }


class Client:
    def __init__(self, config, cache_path, audit_path, transport=None, raw_debug_path=None):
        self.config = config
        self.cache = Cache(cache_path)
        self.audit_path = audit_path
        self.raw_debug_path = raw_debug_path
        self.transport = transport or (MockTransport() if config.provider == "mock" else OpenAITransport(config))

    def generate(self, *, system_prompt, user_prompt, schema, metadata, validator=None):
        stage = metadata.get("stage", "unknown")
        payload = {
            "model": self.config.name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "max_completion_tokens": self.config.max_completion_tokens,
            "response_format": {
                "type": "json_schema",
                "json_schema": {"name": "cocolofa_output", "strict": True, "schema": schema},
            },
        }
        if self.config.temperature is not None:
            payload["temperature"] = self.config.temperature
        if not self.config.structured_output and self.config.provider != "mock":
            payload["response_format"] = {"type": "json_object"}
            payload["messages"][0]["content"] += "\nJSON schema: " + json.dumps(schema)
        key = digest({"config": asdict(self.config), "metadata": metadata, "payload": payload, "schema": schema})
        started = time.monotonic()
        cached = self.cache.get(key)
        if cached is not None:
            validate_output(cached["parsed"], schema)
            if validator:
                validator(cached["parsed"])
            append_jsonl(self.audit_path, {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "metadata": metadata,
                "cache_key": key,
                "cache_hit": True,
                "valid": True,
            })
            return GenerationResult(
                cached["parsed"],
                CallStats(stage, 1, 0, True, 0, 0, 0, 0, time.monotonic() - started, cached.get("model", self.config.name)),
            )

        last_error = None
        feedback = None
        for attempt in range(self.config.max_attempts):
            request_payload = deepcopy(payload)
            if feedback:
                request_payload["messages"].append({
                    "role": "user",
                    "content": "Previous validation failed: " + feedback + ". Return valid JSON only.",
                })
            event = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "metadata": metadata,
                "cache_key": key,
                "cache_hit": False,
                "attempt": attempt + 1,
                "valid": False,
            }
            call_started = time.monotonic()
            response = None
            parsed = None
            retryable = True
            try:
                response = self.transport.complete(request_payload)
                if self.raw_debug_path is not None:
                    append_jsonl(self.raw_debug_path, {"request": request_payload, "response": response, "metadata": metadata})
                choice = response["choices"][0]
                if choice.get("finish_reason") != "stop" or choice["message"].get("refusal"):
                    raise ValueError("Refused, truncated, or non-final response")
                raw = choice["message"].get("content")
                if not isinstance(raw, str):
                    raise ValueError("Missing JSON response text")
                parsed = json.loads(raw)
                validate_output(parsed, schema)
                if validator:
                    validator(parsed)
                event["valid"] = True
                event["model"] = response.get("model", self.config.name)
                event["usage"] = _usage(response)
            except HTTPError as exc:
                last_error = exc
                retryable = exc.code in (408, 409, 429) or 500 <= exc.code <= 599
                event["error"] = f"HTTP {exc.code}"
                event["http_error_body"] = exc.read().decode("utf-8", errors="replace")
            except (URLError, TimeoutError, ConnectionError) as exc:
                last_error = exc
                event["error"] = type(exc).__name__
            except (ValueError, KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
                last_error = exc
                event["error"] = str(exc)
                feedback = str(exc)[:1500]
            event["latency_seconds"] = time.monotonic() - call_started
            append_jsonl(self.audit_path, event)
            if event["valid"]:
                self.cache.put(key, {"parsed": parsed, "response": response, "model": response.get("model", self.config.name)})
                usage = _usage(response)
                return GenerationResult(
                    parsed,
                    CallStats(
                        stage=stage,
                        logical_calls=1,
                        provider_calls=attempt + 1,
                        cache_hit=False,
                        retries=attempt,
                        prompt_tokens=usage["prompt_tokens"],
                        completion_tokens=usage["completion_tokens"],
                        total_tokens=usage["total_tokens"],
                        latency_seconds=time.monotonic() - started,
                        model=response.get("model", self.config.name),
                    ),
                )
            if not retryable:
                raise last_error
            if attempt + 1 < self.config.max_attempts:
                time.sleep(min(60, self.config.backoff_seconds * 2 ** attempt))
        raise ValueError(f"No valid response after {self.config.max_attempts} attempts: {last_error}") from last_error
