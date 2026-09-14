from dataclasses import dataclass

from src.data.loader import ModelInput
from src.engine import Engine


@dataclass
class Result:
    output: dict
    stats: object


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
                "relation": "moral contrast",
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
                "criterion": "exhaustiveness commitment",
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
        return Result(output=output, stats={"stage": stage})


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
