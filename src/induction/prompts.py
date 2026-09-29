import json

from src.io_utils import digest


SEMANTIC_SYSTEM_PROMPT = """You extract latent inferential structure from an argument.
Do not classify the argument and do not assign it to a predefined reasoning subtype.
Read the complete target comment before abstracting it.

First identify premises, then the conclusion, then the inferential bridge, then
direction and polarity. Only after that remove topic-specific content. Preserve
opposite conclusions as opposite directions. Return strict JSON matching the
provided schema. CANONICAL_REASONING must be grammatical prose, not a bag of tags.
Do not treat words such as tradition, historical, always, expert, majority, or
natural as sufficient evidence for a relation. If a field is not applicable,
return null rather than inventing content.
"""


def semantic_extraction_prompt(sample, use_parent_context=False):
    payload = {
        "stage": "semantic_extraction",
        "sample_id": sample["sample_id"],
        "article_id": sample["article_id"],
        "input": {"target": sample["comment"]},
    }
    if use_parent_context:
        payload["input"]["parent_comment"] = sample.get("parent_comment", "")
    return SEMANTIC_SYSTEM_PROMPT, json.dumps(payload, ensure_ascii=False)


def semantic_prompt_hash():
    return digest(SEMANTIC_SYSTEM_PROMPT)

