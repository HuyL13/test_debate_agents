from tests.property_graph.test_extraction import signature
from src.property_graph.normalization import normalize_signature


def test_normalization_emits_structure_not_text():
    features = normalize_signature(signature())
    assert "REL:USED_AS_JUSTIFICATION" in features
    assert "ROLE:premise->conclusion" in features
    assert "SOURCE_TYPE:expert" in features
    assert "SCOPE:individual->universal" in features
    assert not any("Experts agree" in feature for feature in features)
    assert features == sorted(set(features))
