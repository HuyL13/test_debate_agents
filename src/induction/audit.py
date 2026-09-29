import json
import random
from difflib import SequenceMatcher
from pathlib import Path
from collections import Counter

from src.induction.contracts import validate_semantic_record
from src.induction.data import load_positive_samples
from src.io_utils import read_jsonl, write_json


HARD_CASE_IDS = {"262:6182", "70:3658", "463:10685", "587:8959", "582:8342", "262:6784"}


def _normalized(text):
    return " ".join(text.lower().split())


def check_representation_collapse(records, embeddings=None):
    values = [record.get("canonical_reasoning", "").strip() for record in records]
    counts = Counter(values)
    total = len(values)
    unique = len(counts)
    severe = total >= 30 and unique <= max(20, int(total * 0.05))
    near_pairs = 0
    if embeddings is not None and len(embeddings) > 1:
        import numpy as np
        vectors = np.asarray(embeddings, dtype=float)
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        normalized = vectors / np.maximum(norms, 1e-12)
        similarities = normalized @ normalized.T
        near_pairs = int(((similarities > 0.995) & (~np.eye(len(values), dtype=bool))).sum() // 2)
    return {
        "total_count": total,
        "unique_count": unique,
        "unique_ratio": unique / total if total else 0.0,
        "exact_duplicate_representations": sum(count - 1 for count in counts.values() if count > 1),
        "top_repeated_representations": [{"text": text, "count": count} for text, count in counts.most_common(10)],
        "near_duplicate_pairs": near_pairs,
        "severe": severe,
    }


def audit_semantics(config):
    output = Path(config.output_dir)
    output.mkdir(parents=True, exist_ok=True)
    samples, stats = load_positive_samples(config)
    records_path = output / "semantic_records.jsonl"
    records = read_jsonl(records_path) if records_path.exists() else []
    by_key = {}
    duplicate_ids = []
    for row in records:
        sample_id = row.get("sample_id")
        if sample_id in by_key:
            duplicate_ids.append(sample_id)
        elif sample_id:
            by_key[sample_id] = row
    invalid = []
    copied = []
    valid_records = []
    for sample in samples:
        record = by_key.get(sample["sample_id"])
        if record is None:
            continue
        try:
            validate_semantic_record(record, sample)
        except ValueError as exc:
            invalid.append({"sample_id": sample["sample_id"], "error": str(exc)})
            continue
        valid_records.append(record)
        ratio = SequenceMatcher(None, _normalized(record["original_text"]), _normalized(record["canonical_reasoning"])).ratio()
        if ratio >= 0.95:
            copied.append(sample["sample_id"])
    collapse = check_representation_collapse(valid_records)
    ids = {sample["sample_id"] for sample in samples}
    hard_cases = sorted(ids & HARD_CASE_IDS)
    missing_hard_cases = sorted(set(hard_cases) - set(by_key))
    result = {
        "passed": bool(records) and len(by_key) == len(samples) and not duplicate_ids and not invalid and not copied and not collapse["severe"] and not missing_hard_cases,
        "sample_count": len(samples),
        "record_count": len(by_key),
        "duplicate_sample_ids": sorted(set(duplicate_ids)),
        "invalid_records": invalid,
        "copied_canonical_ids": copied,
        "hard_case_ids": hard_cases,
        "missing_hard_case_ids": missing_hard_cases,
        "collapse": collapse,
    }
    write_json(output / "representation_stats.json", collapse)
    write_json(output / "semantic_gate.json", result)
    lines = ["# Semantic Audit", "", f"- Passed: `{result['passed']}`", f"- Samples: `{len(samples)}`", f"- Records: `{len(by_key)}`", "", "## Findings", ""]
    lines.extend([f"- Invalid records: {len(invalid)}", f"- Duplicate sample IDs: {len(set(duplicate_ids))}", f"- Copied canonical representations: {len(copied)}", f"- Severe collapse: {collapse['severe']}"])
    if hard_cases:
        lines.append(f"- Required hard cases inspected: {', '.join(hard_cases)}")
    (output / "semantic_audit.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return result

