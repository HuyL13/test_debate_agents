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


def sample():
    return ModelInput(
        title="Rules",
        parent_comment="",
        comment=(
            "Once you let them dictate rules against fairness, they will continue the problem. "
            "It only gets worse. Rights will be trampled and compromised."
        ),
    )


class IndependentClient:
    def __init__(self):
        self.calls = []

    def generate(self, *, system_prompt, user_prompt, schema, metadata, validator=None):
        self.calls.append(
            {
                "system_prompt": system_prompt,
                "user_prompt": user_prompt,
                "metadata": metadata,
                "schema": schema,
            }
        )
        stage = metadata["stage"]
        if stage == "structure":
            output = {
                "evidence_spans": ["It only gets worse"],
                "structure_type": "consequence_chain",
                "slots": [
                    {"role": "initial_event", "text": "Once you let them dictate rules against fairness"},
                    {"role": "intermediate_consequence", "text": "It only gets worse"},
                    {"role": "final_consequence", "text": "Rights will be trampled and compromised"},
                ],
                "structure_complete": True,
            }
        elif stage == "goal":
            output = {
                "evidence_spans": ["It only gets worse"],
                "conclusion_or_goal": "oppose allowing them to dictate rules",
                "candidate": "Slippery Slope",
                "supporting_reason": "Rights will be lost after allowing the action.",
                "support_relation": "Predicted escalation is used to oppose the action.",
                "label_justification": "The warning assumes unestablished escalation.",
                "mechanism_supports_goal": True,
            }
        elif stage == "counterargument":
            output = {
                "evidence_spans": ["Rights will be trampled and compromised"],
                "decisive_counterargument": "The escalation is asserted without establishing why each consequence follows.",
                "candidate": "Slippery Slope",
                "challenged_inference": "Allowing rules inevitably leads to rights loss.",
                "label_justification": "The objection targets escalation rather than observed cases.",
                "failure_exposed": True,
            }
        else:
            output = {
                "selected_candidate": "Slippery Slope",

                "evidence_spans": ["It only gets worse"],
                "decisive_condition": "consequence_chain",
                "decision_reason": "The target supports the stated escalation hypothesis.",
            }
        output.pop("evidence_spans", None)
        output["evidence_ids"] = ["T1"]
        validate_output(output, schema)
        if validator:
            validator(output)
        return Result(output=output, stats=Stats(stage=stage))


def test_three_experts_receive_raw_input_independently_and_no_gold_leaks():
    client = IndependentClient()
    trace = Engine(client, task="detection").run(
        sample(),
        {"sample_id": "427:6078", "split": "test", "gold": "Fallacious"},
    )

    stages = [call["metadata"]["stage"] for call in client.calls]
    assert stages == ["structure", "goal", "counterargument", "arbiter"]
    for call in client.calls[:3]:
        payload = call["user_prompt"]
        assert '"target": "Once you let them dictate rules against fairness' in payload
        assert "initial_analysis" not in payload
        assert "survivor_support" not in payload
        assert "gold" not in payload
    assert trace["prediction"] == "Fallacious"
    assert trace["selected_candidate"] == "Slippery Slope"
    support = json.loads(client.calls[-1]["user_prompt"])["survivor_support"]["Slippery Slope"]
    by_source = {item["source"]: item for item in support}
    assert by_source["goal"]["support_relation"]
    assert by_source["goal"]["label_justification"]
    assert by_source["counterargument"]["challenged_inference"]
    assert by_source["counterargument"]["label_justification"]


class PruningClient(IndependentClient):
    def generate(self, *, system_prompt, user_prompt, schema, metadata, validator=None):
        self.calls.append({"system_prompt": system_prompt, "user_prompt": user_prompt, "metadata": metadata})
        stage = metadata["stage"]
        if stage == "structure":
            output = {
                "evidence_spans": ["It only gets worse"],
                "structure_type": "exhaustive_alternatives",
                "slots": [],
                "structure_complete": False,
            }
        elif stage == "goal":
            output = {
                "evidence_spans": ["It only gets worse"],
                "conclusion_or_goal": "warn against allowing rules",
                "candidate": "Appeal to Majority",
                "supporting_reason": "Others oppose rules.",
                "support_relation": "Popularity is mentioned but does not support the goal.",
                "label_justification": "Tentative popularity hypothesis is unsupported.",
                "mechanism_supports_goal": False,
            }
        elif stage == "counterargument":
            output = {
                "evidence_spans": ["Rights will be trampled and compromised"],
                "decisive_counterargument": "The escalation is asserted without establishing why each consequence follows.",
                "candidate": "Slippery Slope",
                "challenged_inference": "Allowing rules inevitably leads to rights loss.",
                "label_justification": "The objection targets escalation rather than observed cases.",
                "failure_exposed": True,
            }
        else:
            output = {
                "selected_candidate": "Slippery Slope",

                "evidence_spans": ["It only gets worse"],
                "decisive_condition": "consequence_chain",
                "decision_reason": "The target supports the stated escalation hypothesis.",
            }
        output.pop("evidence_spans", None)
        output["evidence_ids"] = ["T1"]
        if validator:
            validator(output)
        return Result(output=output, stats=Stats(stage=stage))


def test_engine_prunes_nonviable_candidates_before_conflicts_and_binds_arbiter():
    client = PruningClient()
    trace = Engine(client, task="detection").run(sample(), {"sample_id": "427:6078", "split": "test"})

    assert [call["metadata"]["stage"] for call in client.calls] == [
        "structure",
        "goal",
        "counterargument",
        "arbiter",
    ]
    assert trace["conflicts"] == []
    assert trace["candidate_state"]["after_viability"] == ["Slippery Slope"]
    assert trace["candidate_state"]["after_conflicts"] == ["Slippery Slope"]
    arbiter_payload = client.calls[-1]["user_prompt"]
    assert '"surviving_candidates": ["Slippery Slope"]' in arbiter_payload
    assert "False Dilemma" not in arbiter_payload
    assert "Appeal to Majority" not in arbiter_payload
