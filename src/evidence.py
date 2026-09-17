"""TARGET-only evidence references; passages preserve original characters."""
from copy import deepcopy
import re


def target_passages(target):
    words = list(re.finditer(r"\S+", target))
    passages = []
    for index in range(0, len(words), 30):
        start = words[index].start()
        end = words[min(index + 29, len(words) - 1)].end()
        passages.append({"id": f"T{len(passages) + 1}", "start": start,
                         "end": end, "text": target[start:end]})
    return passages


def reference_schema(schema, passages):
    result = deepcopy(schema)
    del result["properties"]["evidence_spans"]
    result["properties"]["evidence_ids"] = {
        "type": "array", "items": {"enum": [p["id"] for p in passages]},
        "minItems": 1 if passages else 0, "maxItems": 3,
    }
    result["required"] = ["evidence_ids" if key == "evidence_spans" else key
                          for key in result["required"]]
    return result


def resolve_evidence(output, passages):
    lookup = {p["id"]: p["text"] for p in passages}
    ids = output["evidence_ids"]
    if any(item not in lookup for item in ids):
        raise ValueError("Evidence IDs must refer to supplied TARGET passages")
    return {**output, "evidence_spans": [lookup[item] for item in ids]}
