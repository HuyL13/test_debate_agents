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
                "evidence_spans": [span],
                "structure_type": "none" if "good and evil" in target else "consequence_chain",
                "slots": [] if "good and evil" in target else [
                    {"role": "initial_event", "text": span},
                    {"role": "intermediate_consequence", "text": span},
                    {"role": "final_consequence", "text": span},
                ],
                "structure_complete": "good and evil" not in target,
            }
        elif "mechanism_supports_goal" in properties:
            if "good and evil" in target:
                value = {
                    "evidence_spans": [span],
                    "conclusion_or_goal": "make a moral contrast",
                    "candidate": None,
                    "supporting_reason": None,
                    "support_relation": None,
                    "label_justification": "Moral contrast alone is not a fallacy.",
                    "mechanism_supports_goal": False,
                }
            else:
                value = {
                    "evidence_spans": [span],
                    "conclusion_or_goal": "warn against the initial action",
                    "candidate": "Slippery Slope",
                "supporting_reason": "Rights will be lost after allowing the action.",
                "support_relation": "Predicted escalation is used to oppose the action.",
                "label_justification": "The warning assumes unestablished escalation.",
                    "mechanism_supports_goal": True,
                }
        elif "failure_exposed" in properties:
            value = {
                "evidence_spans": [span],
                "decisive_counterargument": None if "good and evil" in target else (
                    "The escalation is asserted but not established by the stated reasoning."
                ),
                "candidate": None if "good and evil" in target else "Slippery Slope",
                "challenged_inference": None if "good and evil" in target else "The initial action leads to escalation.",
                "label_justification": "No reasoning defect in the contrast." if "good and evil" in target else "Unestablished escalation supports Slippery Slope.",
                "failure_exposed": "good and evil" not in target,
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
        elif "selected_candidate" in properties:
            selected_schema = properties["selected_candidate"]
            allowed = []

            if "enum" in selected_schema:
                allowed = selected_schema["enum"]
            else:
                for option in selected_schema.get("anyOf", []):
                    allowed.extend(option.get("enum", []))

            if allowed:
                selected = allowed[0]
                value = {
                    "selected_candidate": selected,

                    "evidence_spans": [span],
                    "decisive_condition": (
                        "consequence_chain"
                        if selected == "Slippery Slope"
                        else "target_fallacy_condition"
                    ),
                    "decision_reason": "The target supports the stated escalation hypothesis.",
                }
            else:
                value = {
                    "selected_candidate": None,

                    "evidence_spans": [span],
                    "decisive_condition": "none",
                    "decision_reason": "No surviving hypothesis is supported.",
                }
        else:
            raise ValueError(f"Unknown mock schema for stage: {stage}")
        if "evidence_ids" in properties:
            value.pop("evidence_spans", None)
            value["evidence_ids"] = properties["evidence_ids"]["items"]["enum"][:1]
        return {
            "id": "mock-" + digest({"stage": stage, "target": target})[:12],
            "model": "offline-mock-v1",
            "choices": [{"finish_reason": "stop", "message": {"content": json.dumps(value), "refusal": None}}],
            "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
        }
