from src.prompts import system_prompt


def test_comparative_adjudicator_prompt_defines_symmetric_detection_choice():
    prompt = system_prompt("comparative_arbiter")

    assert "Non-Fallacious" in prompt
    assert "candidate dossiers" in prompt
    assert "sample-to-population" in prompt
    assert "consequence progression" in prompt
    assert "exhaustiveness" in prompt
    assert "deprioritization" in prompt


def test_counterargument_prompt_requires_objection_and_defense():
    prompt = system_prompt("counterargument")

    assert "strongest objection" in prompt.lower()
    assert "strongest defense" in prompt.lower()
    assert "does not force" in prompt.lower()
