import json
from pathlib import Path

from src.induction.contracts import semantic_schema, validate_semantic_record
from src.induction.prompts import semantic_extraction_prompt
from src.io_utils import append_jsonl, read_jsonl, recover_audit_tail


def _key(value):
    return value["article_id"], value["comment_id"]


def _load_records(path):
    if not path.exists():
        return []
    recover_audit_tail(path)
    return read_jsonl(path)


def extract_semantic_records(config, samples, client, resume=False):
    output = Path(config.output_dir)
    output.mkdir(parents=True, exist_ok=True)
    records_path = output / "semantic_records.jsonl"
    failures_path = output / "semantic_failures.jsonl"
    existing = _load_records(records_path) if resume else []
    completed = {_key(record) for record in existing}
    records = list(existing)
    for sample in samples:
        if _key(sample) in completed:
            continue
        system_prompt, user_prompt = semantic_extraction_prompt(sample, config.use_parent_context)
        try:
            result = client.generate(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                schema=semantic_schema(),
                metadata={"stage": "semantic_extraction", "sample_id": sample["sample_id"]},
                validator=lambda value, current=sample: validate_semantic_record(value, current),
            )
            record = validate_semantic_record(result.output, sample)
            append_jsonl(records_path, record)
            records.append(record)
            completed.add(_key(sample))
        except Exception as exc:
            append_jsonl(failures_path, {
                "sample_id": sample["sample_id"],
                "article_id": sample["article_id"],
                "comment_id": sample["comment_id"],
                "error": str(exc),
            })
    expected = {_key(sample) for sample in samples}
    if completed != expected:
        raise RuntimeError(f"semantic extraction incomplete: {len(expected - completed)} samples missing")
    return records

