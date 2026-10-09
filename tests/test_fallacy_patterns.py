"""Unit tests for ArgMining 2026 fallacy pattern integration."""
import pytest

from src.fallacy_patterns import (
    COCOLOFA_PATTERNS,
    get_pattern_enriched_definitions,
    get_logical_role_pattern_guidance,
    get_contextual_role_pattern_guidance,
    get_ars_pattern_rules,
)
from src.prompts import system_prompt
from src.ars_prompts import ars_system_prompt, ROLE_PROMPTS
from src.engine import Engine
from src.labels import FALLACIES
from src.runner import validate_config, ENGINE_DEFAULTS


def test_patterns_taxonomy_completeness():
    assert set(COCOLOFA_PATTERNS.keys()) == set(FALLACIES)
    for name, pattern in COCOLOFA_PATTERNS.items():
        assert hasattr(pattern, 'core_definition')
        assert hasattr(pattern, 'logical_form')
        assert hasattr(pattern, 'reasoning_defect')
        assert hasattr(pattern, 'syntactic_markers')
        assert hasattr(pattern, 'boundary_constraint')
        # Test ASCII encoding safety for Windows terminals
        assert pattern.logical_form.encode('ascii', errors='strict')


def test_pattern_enriched_definitions():
    enriched = get_pattern_enriched_definitions()
    for name in FALLACIES:
        assert f"[{name}]:" in enriched
        assert "Logical Form:" in enriched
        assert "Typical Markers:" in enriched
        assert "Constraint:" in enriched
    assert "CRITICAL DISCRIMINATION RULES:" in enriched


def test_prompts_use_patterns_toggle():
    # Baseline unchanged
    p_logical_base = system_prompt('Logical', 'classification', use_patterns=False)
    p_logical_default = system_prompt('Logical', 'classification')
    assert p_logical_base == p_logical_default
    assert "Ground your reasoning in formal logical patterns:" not in p_logical_base

    # Enriched logical
    p_logical_pat = system_prompt('Logical', 'classification', use_patterns=True)
    assert "Ground your reasoning in formal logical patterns:" in p_logical_pat
    assert "Forced binary disjunction" in p_logical_pat

    # Contextual role
    p_ctx_base = system_prompt('Contextual', 'classification', use_patterns=False)
    assert "Examine linguistic markers and rhetorical framing" not in p_ctx_base
    p_ctx_pat = system_prompt('Contextual', 'classification', use_patterns=True)
    assert "Examine linguistic markers and rhetorical framing" in p_ctx_pat

    # Arbiter role has enriched definitions when use_patterns=True
    p_arb_base = system_prompt('Arbiter', 'classification', use_patterns=False)
    p_arb_pat = system_prompt('Arbiter', 'classification', use_patterns=True)
    assert "Logical Form:" not in p_arb_base
    assert "Logical Form:" in p_arb_pat


def test_ars_prompts_strictly_label_agnostic():
    # Dimension agents must NEVER see fallacy names even if use_patterns=True
    for role in ('Acceptability', 'Relevance', 'Sufficiency'):
        prompt_false = ars_system_prompt(role, 'detection', use_patterns=False)
        prompt_true = ars_system_prompt(role, 'detection', use_patterns=True)
        assert prompt_false == prompt_true
        for fallacy in FALLACIES:
            assert fallacy.lower() not in prompt_true.lower()

    # ARSArbiter receives pattern rules only when use_patterns=True
    arb_false = ars_system_prompt('ARSArbiter', 'detection', use_patterns=False)
    arb_true = ars_system_prompt('ARSArbiter', 'detection', use_patterns=True)
    assert "Logical Form:" not in arb_false
    assert "Logical Form:" in arb_true
    assert "CRITICAL DISCRIMINATION RULES:" in arb_true


def test_engine_use_patterns_validation():
    # Valid boolean
    eng_false = Engine(None, task='detection', use_patterns=False)
    assert eng_false.use_patterns is False
    eng_true = Engine(None, task='detection', use_patterns=True)
    assert eng_true.use_patterns is True

    # Invalid non-boolean
    with pytest.raises(ValueError, match='use_patterns must be boolean'):
        Engine(None, task='detection', use_patterns='yes')


def test_runner_config_validation(tmp_path):
    valid_cfg = {
        'task': 'detection',
        'data_dir': str(tmp_path),
        'split': 'dev',
        'context': 'paper',
        'engine': {'mode': 'adaptive', 'use_patterns': True},
        'model': {'name': 'mock-model', 'provider': 'mock'},
        'output_dir': str(tmp_path / 'out'),
        'cache_dir': str(tmp_path / 'cache'),
    }
    validated = validate_config(valid_cfg)
    assert validated['engine']['use_patterns'] is True

    # Invalid type
    invalid_cfg = dict(valid_cfg)
    invalid_cfg['engine'] = {'use_patterns': 'enabled'}
    with pytest.raises(ValueError, match='use_patterns must be boolean'):
        validate_config(invalid_cfg)
