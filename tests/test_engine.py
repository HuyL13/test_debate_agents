from dataclasses import dataclass
import json

from src.data.loader import ModelInput
from src.engine import Engine
from src.schemas import validate_output


@dataclass
class Result:
    output: dict
    stats: object


@dataclass
class Stats:
    stage: str
    logical_calls: int = 1
    provider_calls: int = 1
    cache_hit: bool = False
    retries: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


INPUT = ModelInput(
    title="Rules",
    parent_comment="",
    comment=(
        "Once you let them dictate rules against fairness, they will continue the problem. "
        "It only gets worse. Rights will be trampled and compromised."
    ),
)


def structure(candidate="Slippery Slope"):
    positive = candidate is not None
    return {
        "verdict": "Fallacious" if positive else "Non-Fallacious",
        "candidate": candidate,
        "mandatory_condition": "An unsupported consequence progression is asserted." if positive else None,
        "condition_satisfied": positive,
        "decision_reason": "The target asserts escalation." if positive else "No listed structure is complete.",
        "opposing_reason": "The warning may be proportionate." if positive else "A compressed escalation may exist.",
        "structure_type": "consequence_chain" if positive else "none",
        "slots": ([
            {"role": "initial_event", "text": "They dictate rules."},
            {"role": "intermediate_consequence", "text": "It gets worse."},
            {"role": "final_consequence", "text": "Rights are trampled."},
        ] if positive else []),
        "structure_complete": positive,
        "premise": "They dictate rules." if positive else None,
        "conclusion": "Rights are trampled." if positive else None,
        "inferential_link": "The action escalates." if positive else None,
    }


def goal(candidate="Slippery Slope"):
    positive = candidate is not None
    return {
        "verdict": "Fallacious" if positive else "Non-Fallacious",
        "candidate": candidate,
        "mandatory_condition": "An unsupported consequence progression is asserted." if positive else None,
        "condition_satisfied": positive,
        "decision_reason": "Escalation supports opposition." if positive else "The warning is proportionate.",
        "opposing_reason": "The warning may be proportionate." if positive else "The escalation may be unsupported.",
        "conclusion_or_goal": "Oppose allowing unfair rules.",
        "supporting_reason": "Rights will be lost.",
        "support_relation": "The predicted loss supports opposition.",
        "label_justification": "The escalation is unsupported." if positive else "No listed fallacy is necessary.",
        "mechanism_supports_goal": True,
        "fallacy_owned_by_target": True,
    }


def counter(candidate="Slippery Slope"):
    positive = candidate is not None
    return {
        "verdict": "Fallacious" if positive else "Non-Fallacious",
        "candidate": candidate,
        "mandatory_condition": "An unsupported consequence progression is asserted." if positive else None,
        "condition_satisfied": positive,
        "decision_reason": "The objection defeats the defense." if positive else "The defense defeats the objection.",
        "opposing_reason": "The defense reads this as a warning." if positive else "The objection alleges escalation.",
        "decisive_counterargument": "No causal support is supplied." if positive else None,
        "challenged_inference": "Allowing rules leads to rights loss." if positive else None,
        "label_justification": "The objection targets escalation." if positive else "No defect is established.",
        "failure_exposed": positive,
        "strongest_objection": "The consequence chain is unsupported.",
        "strongest_defense": "The consequences may be a proportionate warning.",
        "winning_side": "objection" if positive else "defense",
    }


def final(verdict="Fallacious", candidate="Slippery Slope", rejected=None):
    return {
        "selected_verdict": verdict,
        "selected_candidate": candidate,
        "decisive_condition": "The consequence progression is unsupported.",
        "decision_reason": "The target directly asserts escalation.",
        "rejected_candidates": rejected or [],
    }


class ScriptedClient:
    def __init__(self, outputs):
        self.outputs = iter(outputs)
        self.calls = []

    def generate(self, *, system_prompt, user_prompt, schema, metadata, validator=None):
        self.calls.append({
            "system_prompt": system_prompt,
            "user_prompt": user_prompt,
            "schema": schema,
            "metadata": metadata,
        })
        output = {**next(self.outputs), "evidence_ids": ["T1"]}
        validate_output(output, schema)
        if validator:
            validator(output)
        return Result(output=output, stats=Stats(stage=metadata["stage"]))


def test_detection_uses_three_independent_reports_and_one_comparative_call():
    client = ScriptedClient([structure(), goal(), counter(), final()])

    result = Engine(client, task="detection").run(
        INPUT,
        {"sample_id": "427:6078", "split": "test", "gold": "SECRET"},
    )

    assert [call["metadata"]["stage"] for call in client.calls] == [
        "structure", "goal", "counterargument", "comparative_adjudication",
    ]
    for call in client.calls[:3]:
        assert "initial_analysis" not in call["user_prompt"]
        assert "SECRET" not in call["user_prompt"]
    payload = json.loads(client.calls[-1]["user_prompt"])
    assert payload["allowed_candidates"] == ["Slippery Slope"]
    assert payload["non_fallacious_hypothesis"]
    assert payload["candidate_dossiers"][0]["candidate"] == "Slippery Slope"
    assert result["prediction"] == "Fallacious"
    assert result["conflicts"] == []
    assert result["stats"]["logical_calls"] == 4


def test_contested_candidates_are_not_pruned_before_final_call():
    client = ScriptedClient([
        structure(),
        goal(None),
        counter("Hasty Generalization"),
        final(rejected=[{
            "candidate": "Hasty Generalization",
            "failed_condition": "No sample-to-population inference exists.",
        }]),
    ])

    result = Engine(client, task="detection").run(INPUT, {"sample_id": "1:2"})

    payload = json.loads(client.calls[-1]["user_prompt"])
    assert payload["allowed_candidates"] == ["Slippery Slope", "Hasty Generalization"]
    assert all(item["status"] == "contested" for item in result["candidate_state"]["dossiers"])


def test_detection_all_negative_reports_use_full_label_recovery():
    client = ScriptedClient([
        structure(None), goal(None), counter(None),
        final("Non-Fallacious", None),
    ])

    result = Engine(client, task="detection").run(INPUT, {"sample_id": "1:2"})

    payload = json.loads(client.calls[-1]["user_prompt"])
    assert payload["recovery_mode"] is True
    assert len(payload["allowed_candidates"]) == 8
    assert result["prediction"] == "Non-Fallacious"


def test_classification_unanimous_singleton_skips_final_call():
    client = ScriptedClient([structure(), goal(), counter()])

    result = Engine(client, task="classification").run(INPUT, {"sample_id": "1:2"})

    assert [call["metadata"]["stage"] for call in client.calls] == [
        "structure", "goal", "counterargument",
    ]
    assert result["prediction"] == "Slippery Slope"
    assert result["arbiter"]["status"] == "direct_unanimous_singleton"


def test_classification_disagreement_uses_one_comparative_call():
    client = ScriptedClient([
        structure(), goal(None), counter("Hasty Generalization"), final(),
    ])

    result = Engine(client, task="classification").run(INPUT, {"sample_id": "1:2"})

    assert [call["metadata"]["stage"] for call in client.calls] == [
        "structure", "goal", "counterargument", "comparative_adjudication",
    ]
    assert result["prediction"] == "Slippery Slope"


def test_engine_emits_each_stage_as_soon_as_it_completes():
    client = ScriptedClient([structure(), goal(), counter(), final()])
    events = []

    Engine(client, task="detection").run(
        INPUT,
        {"sample_id": "1:2"},
        on_stage=lambda stage, output: events.append((stage, output)),
    )

    assert [stage for stage, _ in events] == [
        "structure", "goal", "counterargument", "comparative_adjudication",
    ]
    assert events[-1][1]["selected_candidate"] == "Slippery Slope"
