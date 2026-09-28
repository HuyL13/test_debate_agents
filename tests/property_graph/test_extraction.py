import json
from types import SimpleNamespace

from src.data.loader import Sample
from src.labels import FALLACIES
from src.property_graph.extraction import extract_samples, extract_signature


def signature(sample_id="1:2"):
    return {
        "sample_id": sample_id,
        "propositions": [
            {"id": "p1", "text": "Experts agree", "speaker": "target", "role": "premise"},
            {"id": "p2", "text": "It is true", "speaker": "target", "role": "conclusion"},
        ],
        "relations": [{
            "source": "p1", "target": "p2", "type": "USED_AS_JUSTIFICATION",
            "status": "asserted", "explicitness": "explicit",
            "evidence_spans": ["Experts agree"],
        }],
        "semantic_roles": {
            "source_type": "expert", "sample_scope": "individual",
            "target_scope": "universal", "alternatives_count": None,
            "property_type": "expertise", "comparison_target": None,
        },
        "qualifiers": {"certainty": "high", "universality": "universal", "normative": False},
        "structural_features": ["premise_to_conclusion"],
        "uncertainties": [],
    }


def sample(sample_id="1:2", fallacy="Appeal to Authority"):
    article_id, comment_id = sample_id.split(":")
    return Sample(
        sample_id, int(article_id), comment_id, "train", "A title",
        "Experts agree. It is true.", "Parent context", "Article", fallacy, False,
    )


class CapturingClient:
    def __init__(self, outputs):
        self.outputs = list(outputs)
        self.calls = []

    def generate(self, **kwargs):
        self.calls.append(kwargs)
        output = self.outputs.pop(0)
        if isinstance(output, Exception):
            raise output
        kwargs["validator"](output)
        stats = SimpleNamespace(provider_calls=1, cache_hit=False, retries=0, total_tokens=10)
        return SimpleNamespace(output=output, stats=stats)


def test_extraction_hides_gold_and_calls_once():
    item = sample()
    client = CapturingClient([signature()])
    record, _ = extract_signature(item, client, "v1")

    assert len(client.calls) == 1
    serialized = json.dumps({key: value for key, value in client.calls[0].items() if key != "validator"})
    assert item.fallacy not in serialized
    assert all(label not in serialized for label in FALLACIES)
    assert record["gold_label"] == item.fallacy
    assert client.calls[0]["metadata"]["sample_id"] == item.sample_id


def test_batch_records_failure_continues_and_resume_skips_completed(tmp_path):
    first = sample("1:2")
    second = sample("1:3", "Appeal to Majority")
    output = tmp_path / "signatures.jsonl"
    failures = tmp_path / "failures.jsonl"
    client = CapturingClient([ValueError("bad response"), signature("1:3")])

    summary = extract_samples([first, second], client, output, failures, prompt_version="v1")

    assert summary["completed"] == 1
    assert summary["failed"] == 1
    assert json.loads(output.read_text(encoding="utf-8").strip())["sample_id"] == "1:3"
    assert json.loads(failures.read_text(encoding="utf-8").strip())["sample_id"] == "1:2"

    resumed = CapturingClient([])
    summary = extract_samples([second], resumed, output, failures, prompt_version="v1", resume=True)
    assert summary["skipped"] == 1
    assert resumed.calls == []
