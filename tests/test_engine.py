from dataclasses import dataclass

from src.data.loader import ModelInput
from src.engine import Engine


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


class RecordingClient:
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
        if stage == "scheme":
            output = {
                "candidate": "False Dilemma",
                "evidence_spans": ["good and evil"],
                "relation": "alternatives_to_choice",
                "structure_complete": False,
            }
        elif stage == "enthymeme":
            output = {
                "candidate": "False Dilemma",
                "evidence_spans": ["good and evil"],
                "required_assumption": "the two moral categories exhaust the options",
                "assumption_licensed": False,
            }
        elif stage == "critical":
            output = {
                "candidate": None,
                "evidence_spans": ["good and evil"],
                "criterion": "exhaustiveness_commitment",
                "criterion_met": False,
                "alternative_reading": "moral rhetoric",
            }
        elif stage.startswith("resolve__"):
            output = {
                "winner": None,
                "evidence_spans": ["good and evil"],
                "decisive_test": "Does TARGET commit to only these choices?",
                "loser_failure": "No exhaustiveness commitment is stated.",
            }
        else:
            output = {"prediction": "Non-Fallacious", "evidence_spans": ["good and evil"]}
        if validator:
            validator(output)
        return Result(output=output, stats=Stats(stage=stage))


def test_engine_runs_only_conflict_guided_stages_without_gold_leakage():
    client = RecordingClient()
    engine = Engine(client, task="detection")
    sample = ModelInput(
        title="Election",
        parent_comment="",
        comment="I think this election is about good and evil.",
    )

    trace = engine.run(sample, {"sample_id": "237:5209", "split": "dev", "gold": "Fallacious"})

    stages = [call["metadata"]["stage"] for call in client.calls]
    assert stages == [
        "scheme",
        "enthymeme",
        "critical",
        "resolve__false-dilemma__vs__non-fallacious",
        "arbiter",
    ]
    assert trace["arbiter"]["prediction"] == "Non-Fallacious"
    prompt_text = "\n".join(call["user_prompt"] for call in client.calls)
    assert "Fallacious" not in prompt_text
    assert "gold" not in prompt_text
    assert "confidence" not in str(trace).lower()
    assert "content" not in str(trace).lower()


class ViabilityClient(RecordingClient):
    def generate(self, *, system_prompt, user_prompt, schema, metadata, validator=None):
        self.calls.append({"system_prompt": system_prompt, "user_prompt": user_prompt, "metadata": metadata})
        stage = metadata["stage"]
        if stage == "scheme":
            output = {
                "candidate": "False Dilemma",
                "evidence_spans": ["It only gets worse"],
                "relation": "alternatives_to_choice",
                "structure_complete": False,
            }
        elif stage == "enthymeme":
            output = {
                "candidate": "Appeal to Authority",
                "evidence_spans": ["let them dictate rules against fairness"],
                "required_assumption": "rule-makers are authoritative support for the conclusion",
                "assumption_licensed": False,
            }
        elif stage == "critical":
            output = {
                "candidate": "Slippery Slope",
                "evidence_spans": ["It only gets worse", "Rights will be trampled and compromised"],
                "criterion": "consequence_progression",
                "criterion_met": True,
                "alternative_reading": None,
            }
        else:
            output = {"prediction": "Non-Fallacious", "evidence_spans": ["It only gets worse"]}
        if validator:
            validator(output)
        return Result(output=output, stats=Stats(stage=stage))


def test_engine_prunes_nonviable_candidates_before_conflicts_and_binds_arbiter():
    client = ViabilityClient()
    engine = Engine(client, task="detection")
    sample = ModelInput(
        title="Rules",
        parent_comment="",
        comment=(
            "Once you let them dictate rules against fairness, they will continue the problem. "
            "It only gets worse. Rights will be trampled and compromised."
        ),
    )

    trace = engine.run(sample, {"sample_id": "427:6078", "split": "test"})

    assert [call["metadata"]["stage"] for call in client.calls] == [
        "scheme",
        "enthymeme",
        "critical",
        "arbiter",
    ]
    assert trace["conflicts"] == []
    assert trace["candidate_state"]["after_viability"] == ["Slippery Slope"]
    assert trace["candidate_state"]["after_conflicts"] == ["Slippery Slope"]
    assert trace["arbiter"]["prediction"] == "Non-Fallacious"
    assert trace["prediction"] == "Fallacious"
    arbiter_payload = client.calls[-1]["user_prompt"]
    assert '"surviving_candidates": ["Slippery Slope"]' in arbiter_payload
