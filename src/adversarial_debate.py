"""Execution engine for Adversarial Dialectical Debate (Prosecutor vs. Defender)."""

from typing import Any, Callable, Dict, Tuple
from src.data.loader import ModelInput
from src.adversarial_schemas import (
    prosecutor_schema,
    defender_schema,
    dialectical_arbiter_schema,
    validate_prosecutor,
    validate_defender,
    validate_dialectical_arbiter,
)


def execute(
    ask: Callable[..., Dict[str, Any]],
    model_input: ModelInput,
    task: str,
    use_patterns: bool = True,
) -> Tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any], str]:
    """Execute the 2-to-3 call adversarial debate pipeline.

    Returns:
        (prosecutor_report, defender_report, arbiter_verdict, stop_reason)
    """
    # Stage 1: Prosecutor Indictment
    prosecutor = ask(
        'Prosecutor',
        'indictment',
        {},
        [],
        'Scrutinize the target comment for candidate logical fallacies matching the benchmark taxonomy.',
        schema=prosecutor_schema(),
        validator=lambda val: validate_prosecutor(val, model_input.comment),
    )

    has_charge = prosecutor.get('has_fallacy_charge', False)

    if not has_charge:
        # Case A: Prosecutor found no fallacy charge (Early Exit / Swift Confirmation)
        defender = {
            'concede_charge': False,
            'charitable_interpretation': 'No fallacy charge was brought by the Prosecutor.',
            'counter_quote': '',
        }
        arbiter = ask(
            'DialecticalArbiter',
            'verdict',
            {'prosecutor': prosecutor, 'defender': defender},
            [],
            'Review the unindicted target comment and issue the official verdict.',
            schema=dialectical_arbiter_schema(task),
            validator=lambda val: validate_dialectical_arbiter(val, task),
        )
        return prosecutor, defender, arbiter, 'no_charge_dismissed'

    # Case B: Prosecutor brought a formal fallacy charge -> Activate Defender
    defender = ask(
        'Defender',
        'plea',
        {'prosecutor_indictment': prosecutor},
        [],
        'Apply the Principle of Charity. Defend the target comment against the Prosecutor indictment using context.',
        schema=defender_schema(),
        validator=lambda val: validate_defender(val, model_input.comment),
    )

    # Stage 3: Dialectical Arbiter Verdict
    arbiter = ask(
        'DialecticalArbiter',
        'verdict',
        {'prosecutor': prosecutor, 'defender': defender},
        [],
        'Weigh the Prosecutor indictment against the Defender plea under the burden of proof. Issue final verdict.',
        schema=dialectical_arbiter_schema(task),
        validator=lambda val: validate_dialectical_arbiter(val, task),
    )

    return prosecutor, defender, arbiter, 'contested_adjudication'
