"""Execution engine for Adversarial Dialectical Debate (Prosecutor vs. Defender)."""

from typing import Any, Callable, Dict, Tuple
from src.data.loader import ModelInput
from src.dialectical.schemas import (
    prosecutor_schema,
    defender_schema,
    dialectical_arbiter_schema,
    arbiter_pairwise_schema,
    validate_prosecutor,
    validate_defender,
    validate_dialectical_arbiter,
    validate_arbiter_pairwise,
)
from src.dialectical.validation import validate_and_normalize_defender
from src.schemas import _normalize_quote_text


def execute(
    ask: Callable[..., Dict[str, Any]],
    model_input: ModelInput,
    task: str,
    use_patterns: bool = True,
) -> Tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any], str]:
    """Execute the adversarial debate pipeline for detection or classification.

    Returns:
        (prosecutor_report, defender_report, arbiter_verdict, stop_reason)
    """
    if task == 'classification':
        # Stage 1: Prosecutor Indictment
        prosecutor = ask(
            'Prosecutor',
            'indictment',
            {},
            [],
            'Run CUE SCAN, separate justificatory premise from conclusion, and output top-2 candidate classes with verbatim quotes. '
            'IMPORTANT: Both quote and runner_up_quote MUST be exact verbatim substrings copied ONLY from the TARGET comment (input.comment). '
            'Do NOT quote from parent_comment or title!',
            schema=prosecutor_schema('classification'),
            validator=lambda val: validate_prosecutor(val, model_input.comment, 'classification'),
        )

        def _validate_defender_plea(val):
            cand_q = prosecutor.get('quote', '')
            c_q = val.get('counter_quote', '')
            if val.get('alternative_class') in ('None', prosecutor.get('candidate_class')) and not val.get('concede_charge'):
                if c_q and cand_q and _normalize_quote_text(c_q).casefold() == _normalize_quote_text(cand_q).casefold():
                    val['concede_charge'] = True
                    val['alternative_class'] = 'None'
            validate_defender(val, model_input, 'classification')

        # Stage 2: Defender Competing Class Advocacy
        defender = ask(
            'Defender',
            'plea',
            {'prosecutor_indictment': prosecutor},
            [],
            'Evaluate the Prosecutor indictment against target comment and context. '
            'If the Prosecutor correctly identified an Appeal, False Dilemma, or Slippery Slope with a valid quote, set concede_charge=true. '
            'Do NOT default to Hasty Generalization. If a competing class has genuine structural evidence, steelman it with a verbatim quote.',
            schema=defender_schema('classification'),
            validator=_validate_defender_plea,
        )

        # Code-level Validator before Arbiter:
        # Enforces: alt == candidate -> concede; quote substring, non-identical, length >= 5;
        # structural cue match; cue-locking protection.
        defender = validate_and_normalize_defender(prosecutor, defender, model_input.comment)

        cand_class = prosecutor.get('candidate_class')
        cand_quote = prosecutor.get('quote')

        # Case A: Agreed / Conceded Classification (Uncontested)
        if defender.get('concede_charge'):
            payload_uncontested = {
                'comment': model_input.comment,
                'candidate': {'class': cand_class, 'quote': cand_quote},
            }
            arbiter = ask(
                'DialecticalArbiter',
                'verdict',
                payload_uncontested,
                [],
                f"Confirm the uncontested candidate class '{cand_class}' against TARGET comment.",
                schema=dialectical_arbiter_schema('classification'),
                validator=lambda val: validate_dialectical_arbiter(val, 'classification'),
            )
            # Ensure uncontested prediction reflects candidate class
            if arbiter.get('prediction') != cand_class:
                arbiter['prediction'] = cand_class
            return prosecutor, defender, arbiter, 'agreed_classification'

        # Case B: Contested Classification -> Order-Permuted Adjudication
        alt_class = defender.get('alternative_class')
        alt_quote = defender.get('counter_quote')

        # Run A: Order 1 (Option 1 = Cand, Option 2 = Alt)
        payload_a = {
            'comment': model_input.comment,
            'option_1': {'class': cand_class, 'quote': cand_quote},
            'option_2': {'class': alt_class, 'quote': alt_quote},
        }
        verdict_a = ask(
            'DialecticalArbiter',
            'verdict_run_a',
            payload_a,
            [],
            f"Adjudicate strictly between Option 1 ({cand_class}) and Option 2 ({alt_class}). "
            f"Rule strictly based on which verbatim quote demonstrates the genuine structural defect of that class.",
            schema=arbiter_pairwise_schema(cand_class, alt_class),
            validator=lambda val: validate_arbiter_pairwise(val, cand_class, alt_class),
        )

        # Run B: Order 2 - Swapped (Option 1 = Alt, Option 2 = Cand)
        payload_b = {
            'comment': model_input.comment,
            'option_1': {'class': alt_class, 'quote': alt_quote},
            'option_2': {'class': cand_class, 'quote': cand_quote},
        }
        verdict_b = ask(
            'DialecticalArbiter',
            'verdict_run_b',
            payload_b,
            [],
            f"Adjudicate strictly between Option 1 ({alt_class}) and Option 2 ({cand_class}). "
            f"Rule strictly based on which verbatim quote demonstrates the genuine structural defect of that class.",
            schema=arbiter_pairwise_schema(alt_class, cand_class),
            validator=lambda val: validate_arbiter_pairwise(val, alt_class, cand_class),
        )

        # Unanimous Challenger Burden of Proof: Only flip if BOTH orderings agree on Alternative!
        pred_a = verdict_a.get('prediction')
        pred_b = verdict_b.get('prediction')
        if pred_a == alt_class and pred_b == alt_class:
            final_pred = alt_class
            avg_conf = (verdict_a.get('confidence', 0.8) + verdict_b.get('confidence', 0.8)) / 2.0
            arbiter_content = (
                f"Order-permuted consensus: Both runs ruled for Alternative '{alt_class}'. "
                f"Run A: {verdict_a.get('content')}; Run B: {verdict_b.get('content')}"
            )
        else:
            final_pred = cand_class
            avg_conf = (verdict_a.get('confidence', 0.8) + verdict_b.get('confidence', 0.8)) / 2.0
            arbiter_content = (
                f"Alternative failed unanimous burden of proof (Run A: {pred_a}, Run B: {pred_b}). "
                f"Upholding Prosecutor candidate '{cand_class}'."
            )

        arbiter = {
            'prediction': final_pred,
            'confidence': round(avg_conf, 2),
            'content': arbiter_content,
            'permuted_runs': [verdict_a, verdict_b],
        }
        return prosecutor, defender, arbiter, 'contested_classification'


    # Detection task
    # Stage 1: Prosecutor Indictment
    prosecutor = ask(
        'Prosecutor',
        'indictment',
        {},
        [],
        'Scrutinize the target comment for candidate logical fallacies matching the benchmark taxonomy.',
        schema=prosecutor_schema('detection'),
        validator=lambda val: validate_prosecutor(val, model_input.comment, 'detection'),
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
            schema=dialectical_arbiter_schema('detection'),
            validator=lambda val: validate_dialectical_arbiter(val, 'detection'),
        )
        return prosecutor, defender, arbiter, 'no_charge_dismissed'

    # Case B: Prosecutor brought a formal fallacy charge -> Activate Defender
    defender = ask(
        'Defender',
        'plea',
        {'prosecutor_indictment': prosecutor},
        [],
        'Apply the Principle of Charity. Defend the target comment against the Prosecutor indictment using context.',
        schema=defender_schema('detection'),
        validator=lambda val: validate_defender(val, model_input.comment, 'detection'),
    )

    # Stage 3: Dialectical Arbiter Verdict
    arbiter = ask(
        'DialecticalArbiter',
        'verdict',
        {'prosecutor': prosecutor, 'defender': defender},
        [],
        'Weigh the Prosecutor indictment against the Defender plea under the burden of proof. Issue final verdict.',
        schema=dialectical_arbiter_schema('detection'),
        validator=lambda val: validate_dialectical_arbiter(val, 'detection'),
    )

    return prosecutor, defender, arbiter, 'contested_adjudication'
