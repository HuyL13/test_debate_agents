"""Deterministic conversion from signatures to structural features."""


def normalize_signature(signature):
    propositions = {item["id"]: item for item in signature["propositions"]}
    features = set()
    for relation in signature["relations"]:
        features.add(f"REL:{relation['type']}")
        source_role = propositions[relation["source"]]["role"]
        target_role = propositions[relation["target"]]["role"]
        features.add(f"ROLE:{source_role}->{target_role}")
        features.add(f"EXPLICITNESS:{relation['explicitness']}")
    roles = signature["semantic_roles"]
    if roles["source_type"] is not None:
        features.add(f"SOURCE_TYPE:{roles['source_type']}")
    if roles["property_type"] is not None:
        features.add(f"PROPERTY_TYPE:{roles['property_type']}")
    if roles["sample_scope"] is not None or roles["target_scope"] is not None:
        features.add(
            f"SCOPE:{roles['sample_scope'] or 'unspecified'}->{roles['target_scope'] or 'unspecified'}"
        )
    if roles["alternatives_count"] is not None:
        features.add(f"ALTERNATIVES_COUNT:{roles['alternatives_count']}")
    qualifiers = signature["qualifiers"]
    if qualifiers["certainty"] is not None:
        features.add(f"CERTAINTY:{qualifiers['certainty']}")
    if qualifiers["universality"] is not None:
        features.add(f"QUALIFIER:{qualifiers['universality']}")
    if qualifiers["normative"]:
        features.add("QUALIFIER:normative")
    for item in signature["structural_features"]:
        features.add(f"STRUCTURE:{item}")
    return sorted(features)

