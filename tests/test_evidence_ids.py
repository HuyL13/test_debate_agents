import pytest
from src.evidence import target_passages, reference_schema, resolve_evidence
from src.schemas import structure_schema, validate_output


def test_passages_preserve_characters_and_offsets():
    target = "I've seen  this\n... " + "word " * 70
    passages = target_passages(target)
    assert len(passages) == 3
    for p in passages:
        assert p["text"] == target[p["start"]:p["end"]]
    output = resolve_evidence({"evidence_ids": ["T1", "T3"]}, passages)
    assert output["evidence_spans"] == [passages[0]["text"], passages[2]["text"]]


def test_wire_schema_rejects_quotes_and_unknown_ids():
    passages = target_passages("Original TARGET")
    schema = reference_schema(structure_schema("detection"), passages)
    base = {"structure_type": "none", "slots": [], "structure_complete": False}
    validate_output({**base, "evidence_ids": ["T1"]}, schema)
    for fields in ({"evidence_ids": ["P1"]}, {"evidence_spans": ["Original ..."]}):
        with pytest.raises(ValueError):
            validate_output({**base, **fields}, schema)
    with pytest.raises(ValueError):
        resolve_evidence({"evidence_ids": ["T2"]}, passages)


def test_empty_target_has_no_invented_evidence():
    assert target_passages("  ") == []
    assert resolve_evidence({"evidence_ids": []}, [])["evidence_spans"] == []


def test_engine_resolves_ids_after_cache_without_polluting_wire_output(tmp_path):
    from src.llm.client import Client, ModelConfig
    from src.engine import Engine
    from src.data.loader import ModelInput
    client = Client(ModelConfig(name="mock", provider="mock"),
                    tmp_path / "cache.sqlite", tmp_path / "audit.jsonl")
    engine = Engine(client, task="detection")
    sample = ModelInput(title="Context only", parent_comment="Parent only", comment="It  gets worse.")
    first = engine.run(sample, {"sample_id": "test"})
    second = engine.run(sample, {"sample_id": "test"})
    assert second["stats"]["provider_calls"] == 0
    assert first["initial_analysis"] == second["initial_analysis"]
    for report in second["initial_analysis"].values():
        assert report["evidence_ids"] == ["T1"]
        assert report["evidence_spans"] == [sample.comment]
