from copy import deepcopy
import pytest
import yaml
from src.courtroom_rl.data import ROOT, load_cases, load_development_cases


def test_configured_development_is_exact_dialectical66_and_public_input_only():
    config=yaml.safe_load((ROOT/'configs/courtroom_rl.yaml').read_text())
    cases=load_development_cases(config)
    assert len(cases)==66
    official={c.sample_id:c for c in load_cases('test')}
    for case in cases:
        assert case.gold==official[case.sample_id].gold
        assert case.input==official[case.sample_id].input
        assert set(case.input.as_dict())=={'title','parent_comment','comment'}
    assert not {c.sample_id for c in cases}&{c.sample_id for c in load_cases('train')}


def test_diagnostic_dev_rejects_wrong_checksum():
    config=yaml.safe_load((ROOT/'configs/courtroom_rl.yaml').read_text())
    config=deepcopy(config);config['development_set']['sha256']='0'*64
    with pytest.raises(ValueError,match='checksum'):
        load_development_cases(config)
