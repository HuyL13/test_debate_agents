import json
from pathlib import Path

from src.induction.contracts import semantic_schema, validate_semantic_record
from src.induction.prompts import semantic_extraction_prompt
from src.io_utils import append_jsonl, read_jsonl, recover_audit_tail, write_jsonl


def _key(value):
    return value["sample_id"]


def _load_records(path):
    if not path.exists():
        return []
    recover_audit_tail(path)
    return read_jsonl(path)


def _bind_sample_ids(record, sample):
    # IDs identify the request, not a semantic field the model should infer.
    # Bind them before validation so a model cannot attach valid content to a
    # different sample; original_text remains strictly validated below.
    record["sample_id"] = sample["sample_id"]
    return record


def _normalize_model_record(record, sample):
    _bind_sample_ids(record, sample)
    return record


def _deduplicate_valid_records(records, samples):
    samples_by_key = {_key(sample): sample for sample in samples}
    unique = {}
    for record in records:
        try:
            key = _key(record)
        except (KeyError, TypeError):
            continue
        sample = samples_by_key.get(key)
        if sample is None:
            continue
        try:
            normalized = _normalize_model_record(dict(record), sample)
            unique[key] = dict(validate_semantic_record(normalized, sample))
        except (KeyError, TypeError, ValueError):
            continue
    return list(unique.values())


def _compact_failures(path, samples, completed):
    if not path.exists():
        return
    samples_by_key = {_key(sample): sample for sample in samples}
    unique = {}
    for failure in _load_records(path):
        try:
            key = _key(failure)
        except (KeyError, TypeError):
            continue
        if key in samples_by_key and key not in completed:
            unique[key] = failure
    write_jsonl(path, list(unique.values()))


def extract_semantic_records(config, samples, client, resume=False):
    output = Path(config.output_dir)
    output.mkdir(parents=True, exist_ok=True)
    records_path = output / "semantic_records.jsonl"
    failures_path = output / "semantic_failures.jsonl"
    existing = _load_records(records_path) if resume and records_path.exists() else []
    if resume and records_path.exists():
        existing = _deduplicate_valid_records(existing, samples)
        write_jsonl(records_path, existing)
    completed = {_key(record) for record in existing}
    if resume:
        _compact_failures(failures_path, samples, completed)
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
                validator=lambda value, current=sample: validate_semantic_record(
                    _normalize_model_record(value, current), current
                ),
            )
            record = dict(validate_semantic_record(_normalize_model_record(result.output, sample), sample))
            record["sample_id"] = sample["sample_id"]
            append_jsonl(records_path, record)
            records.append(record)
            completed.add(_key(sample))
        except Exception as exc:
            append_jsonl(failures_path, {
                "sample_id": sample["sample_id"],
                "error": str(exc),
            })
    _compact_failures(failures_path, samples, completed)
    expected = {_key(sample) for sample in samples}
    if completed != expected:
        raise RuntimeError(f"semantic extraction incomplete: {len(expected - completed)} samples missing")
    return records

