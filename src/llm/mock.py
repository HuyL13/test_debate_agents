"""Deterministic transport for plumbing smoke tests. NOT an LLM or benchmark."""
import json

from src.io_utils import digest


def _target(payload):
    user = json.loads(payload["messages"][1]["content"])
    return user["input"]["target"]


def _span(text):
    return text[:120] if text else "empty"


class MockTransport:
    def complete(self, payload):
        properties = payload["response_format"]["json_schema"]["schema"]["properties"]
        stage = json.loads(payload["messages"][1]["content"]).get("stage", "")
        target = _target(payload)
        span = "good and evil" if "good and evil" in target else _span(target)
        if "structure_complete" in properties:
            value = {
                "candidate": "False Dilemma" if "good and evil" in target else "Slippery Slope",
                "evidence_spans": [span],
                "relation": "offline structural fixture",
                "structure_complete": "only" in target.lower(),
            }
        elif "assumption_licensed" in properties:
            value = {
                "candidate": "False Dilemma" if "good and evil" in target else "Slippery Slope",
                "evidence_spans": [span],
                "required_assumption": "the options are exhaustive" if "good and evil" in target else None,
                "assumption_licensed": "only" in target.lower() or "good and evil" not in target,
            }
        elif "criterion_met" in properties:
            value = {
                "candidate": None if "good and evil" in target else "Slippery Slope",
                "evidence_spans": [span],
                "criterion": "mandatory target structure",
                "criterion_met": "good and evil" not in target,
                "alternative_reading": "offline non-fallacious reading",
            }
        elif "winner" in properties:
            allowed = properties["winner"].get("enum") or properties["winner"]["anyOf"][0].get("enum", [])
            winner = None if any(item.get("type") == "null" for item in properties["winner"].get("anyOf", [])) else allowed[0]
            value = {
                "winner": winner,
                "evidence_spans": [span],
                "decisive_test": "offline targeted discriminator",
                "loser_failure": "offline losing mandatory condition failed",
            }
        else:
            labels = properties["prediction"]["enum"]
            value = {
                "prediction": "Non-Fallacious" if "Non-Fallacious" in labels and "good and evil" in target else labels[-1],
                "evidence_spans": [span],
            }
        return {
            "id": "mock-" + digest({"stage": stage, "target": target})[:12],
            "model": "offline-mock-v1",
            "choices": [{"finish_reason": "stop", "message": {"content": json.dumps(value), "refusal": None}}],
            "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
        }
