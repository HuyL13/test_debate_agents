import json

from src.llm.client import Client, GenerationResult, ModelConfig
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
