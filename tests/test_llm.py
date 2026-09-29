import json
from io import BytesIO
from urllib.error import HTTPError

import pytest

from src.llm.client import Client, GenerationResult, ModelConfig, RateLimitError
from src.schemas import arbiter_schema


def envelope(content):
    return {
        "id": "response-id",
        "model": "fixture-model",
        "choices": [{"finish_reason": "stop", "message": {"content": content, "refusal": None}}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
    }


class Transport:
    def __init__(self, responses):
        self.responses = iter(responses)
        self.requests = []

    def complete(self, payload):
        self.requests.append(payload)
        return next(self.responses)


def test_client_returns_output_with_call_stats_and_cache_hit(tmp_path):
    output = {
        "selected_candidate": "Slippery Slope",

        "evidence_spans": ["x"],
        "decisive_condition": "consequence_chain",
        "decision_reason": "The target supports the stated escalation hypothesis.",
    }
    transport = Transport([envelope(json.dumps(output))])
    client = Client(
        ModelConfig(name="fixture-model", provider="mock"),
        tmp_path / "cache.sqlite",
        tmp_path / "api_calls.jsonl",
        transport=transport,
    )

    first = client.generate(
        system_prompt="Analyze.",
        user_prompt=json.dumps({"input": {"comment": "x"}}),
        schema=arbiter_schema("detection", ["Slippery Slope"]),
        metadata={"stage": "arbiter"},
    )
    second = client.generate(
        system_prompt="Analyze.",
        user_prompt=json.dumps({"input": {"comment": "x"}}),
        schema=arbiter_schema("detection", ["Slippery Slope"]),
        metadata={"stage": "arbiter"},
    )

    assert isinstance(first, GenerationResult)
    assert first.output["selected_candidate"] == "Slippery Slope"
    assert first.stats.provider_calls == 1
    assert first.stats.total_tokens == 15
    assert second.stats.cache_hit is True
    assert second.stats.provider_calls == 0
    assert len(transport.requests) == 1
    audit = (tmp_path / "api_calls.jsonl").read_text(encoding="utf-8")
    assert '"request"' not in audit
    assert '"response"' not in audit


def test_client_reports_provider_finish_reason_for_non_final_response(tmp_path):
    response = envelope("{}")
    response["choices"][0]["finish_reason"] = "length"
    transport = Transport([response])
    client = Client(
        ModelConfig(name="fixture-model", provider="mock", max_attempts=1),
        tmp_path / "cache.sqlite",
        tmp_path / "api_calls.jsonl",
        transport=transport,
    )

    with pytest.raises(ValueError, match="finish_reason=length"):
        client.generate(
            system_prompt="Analyze.",
            user_prompt=json.dumps({"input": {"comment": "x"}}),
            schema=arbiter_schema("detection", ["Slippery Slope"]),
            metadata={"stage": "arbiter"},
        )


def test_client_increases_completion_budget_after_length_response(tmp_path):
    output = {
        "selected_candidate": "Slippery Slope",
        "evidence_spans": ["x"],
        "decisive_condition": "consequence_chain",
        "decision_reason": "The target supports the stated escalation hypothesis.",
    }
    truncated = envelope("{}")
    truncated["choices"][0]["finish_reason"] = "length"
    transport = Transport([truncated, envelope(json.dumps(output))])
    client = Client(
        ModelConfig(
            name="fixture-model",
            provider="mock",
            max_attempts=2,
            max_completion_tokens=1200,
            backoff_seconds=0,
        ),
        tmp_path / "cache.sqlite",
        tmp_path / "api_calls.jsonl",
        transport=transport,
    )

    result = client.generate(
        system_prompt="Analyze.",
        user_prompt=json.dumps({"input": {"comment": "x"}}),
        schema=arbiter_schema("detection", ["Slippery Slope"]),
        metadata={"stage": "arbiter"},
    )

    assert result.output["selected_candidate"] == "Slippery Slope"
    assert transport.requests[0]["max_completion_tokens"] == 1200
    assert transport.requests[1]["max_completion_tokens"] == 2400


def test_client_preserves_rate_limit_and_retry_after(tmp_path):
    error = HTTPError(
        "https://example.test/chat/completions",
        429,
        "Too Many Requests",
        {"Retry-After": "7"},
        BytesIO(b'{"error":"rate limited"}'),
    )

    class RateLimitedTransport:
        def complete(self, payload):
            raise error

    client = Client(
        ModelConfig(name="fixture-model", provider="mock", max_attempts=1),
        tmp_path / "cache.sqlite",
        tmp_path / "api_calls.jsonl",
        transport=RateLimitedTransport(),
    )

    with pytest.raises(RateLimitError) as caught:
        client.generate(
            system_prompt="Analyze.",
            user_prompt=json.dumps({"input": {"comment": "x"}}),
            schema=arbiter_schema("detection", ["Slippery Slope"]),
            metadata={"stage": "arbiter"},
        )

    assert caught.value.retry_after == 7
