"""Leakage-safe, one-call argument-signature extraction."""

import json
from pathlib import Path

from src.io_utils import append_jsonl, read_jsonl
from src.property_graph.schemas import (
    PROPOSITION_ROLES,
    RELATION_TYPES,
    SIGNATURE_JSON_SCHEMA,
    SIGNATURE_SCHEMA_VERSION,
    SPEAKER_ROLES,
    validate_signature,
)


PROMPT_VERSION = "v1"
SYSTEM_PROMPT = """Extract the argumentative structure of TARGET.
TITLE and PARENT are context only. Do not classify, name, or infer a fallacy.
Return JSON matching the supplied schema. Use only these proposition roles:
{roles}. Use only these speaker roles: {speakers}. Use only these relation types:
{relations}. Evidence spans must be verbatim substrings of TITLE, PARENT, or TARGET.
Represent uncertainty explicitly and do not invent unsupported relations.""".format(
    roles=", ".join(PROPOSITION_ROLES),
    speakers=", ".join(SPEAKER_ROLES),
    relations=", ".join(RELATION_TYPES),
)


def build_extraction_prompts(sample):
    visible = {
        "title": sample.title,
        "parent": sample.parent_comment,
        "target": sample.comment,
    }
    user_prompt = json.dumps(
        {"stage": "property_graph_extraction", "input": visible, "sample_id": sample.sample_id},
        ensure_ascii=False,
    )
    return SYSTEM_PROMPT, user_prompt


def extract_signature(sample, client, prompt_version=PROMPT_VERSION):
    system_prompt, user_prompt = build_extraction_prompts(sample)
    visible = json.loads(user_prompt)["input"]
    visible_text = "\n".join(visible.values())

    def validator(output):
        validate_signature(output, visible_text)
        if output["sample_id"] != sample.sample_id:
            raise ValueError("signature sample_id does not match requested sample")

    result = client.generate(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        schema=SIGNATURE_JSON_SCHEMA,
        metadata={
            "stage": "property_graph_extraction",
            "sample_id": sample.sample_id,
            "split": sample.split,
            "prompt_version": prompt_version,
            "schema_version": SIGNATURE_SCHEMA_VERSION,
        },
        validator=validator,
    )
    record = {
        "sample_id": sample.sample_id,
        "split": sample.split,
        "raw_signature": result.output,
        "gold_label": sample.fallacy,
    }
    return record, result.stats


def extract_samples(
    samples,
    client,
    output_path,
    failures_path,
    *,
    prompt_version=PROMPT_VERSION,
    resume=False,
):
    output_path = Path(output_path)
    failures_path = Path(failures_path)
    completed_ids = set()
    if resume and output_path.exists():
        completed_ids = {row["sample_id"] for row in read_jsonl(output_path)}

    summary = {
        "requested": len(samples),
        "completed": 0,
        "failed": 0,
        "skipped": 0,
        "provider_calls": 0,
        "cache_hits": 0,
        "retries": 0,
        "total_tokens": 0,
    }
    for sample in samples:
        if sample.sample_id in completed_ids:
            summary["skipped"] += 1
            continue
        try:
            record, stats = extract_signature(sample, client, prompt_version)
            append_jsonl(output_path, record)
            summary["completed"] += 1
            summary["provider_calls"] += stats.provider_calls
            summary["cache_hits"] += int(stats.cache_hit)
            summary["retries"] += stats.retries
            summary["total_tokens"] += stats.total_tokens
        except Exception as exc:
            append_jsonl(failures_path, {
                "sample_id": sample.sample_id,
                "error": f"{type(exc).__name__}: {exc}",
            })
            summary["failed"] += 1
    return summary

