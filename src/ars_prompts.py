from src.labels import labels_for


ARS_COMMON = (
    'Use only the supplied TITLE, ARTICLE when present, '
    'IMMEDIATE PARENT COMMENT, and TARGET COMMENT. '
    'Judge only reasoning attributable to TARGET. '
    'Do not use external facts or memory to fact-check the world. '
    'Treat the decomposition as a fallible hypothesis. '
    'Verify it against the raw input before accepting it. '
    'Preserve modality, quantifiers, negation, scope, timing, '
    'conditionality and uncertainty. '
    'Do not output a task label. '
    'Do not name a logical-fallacy class. '
    'Missing citations, strong opinions, advocacy, predictions, '
    'normative language or unavailable external evidence do not '
    'automatically establish a reasoning defect. '
    'Return only JSON matching the provided schema. '
)


DECOMPOSER_PROMPT = (
    'You are an argument-structure decomposer. '
    'Your only task is to represent the structure of the supplied argument. '
    'Extract claims verbatim and preserve their source provenance. '
    'Preserve qualifiers such as may, might, could, should, probably, '
    'sometimes, usually, some, many, all and conditionals. '
    'Distinguish premise, conclusion, intermediate conclusion, '
    'evidence, background, stance and other material. '
    'Reconstruct only minimal implicit assumptions licensed by '
    'linguistic form, context, speaker commitment or argument structure. '
    'Do not invent assumptions merely to make the argument complete. '
    'If structure is uncertain, record uncertainty. '
    'Build explicit inference links between claims and assumptions. '
    'Do not evaluate whether the argument is good or bad. '
)


ACCEPTABILITY_PROMPT = (
    'You are the Acceptability specialist. '
    'Evaluate ACCEPTABILITY only. '
    'Ask whether the premises or commitments can be provisionally '
    'accepted based on the supplied text and context. '
    'Do not fact-check external reality. '
    'If acceptability depends on unavailable outside knowledge, '
    'use dimension_status=not_applicable. '
    'Distinguish lack of external verification from contradiction '
    'or weakness visible in the supplied text itself. '
    'Do not evaluate whether a premise is relevant to the conclusion. '
    'Do not evaluate whether the total support is sufficient. '
    'Do not classify the argument. '
)


RELEVANCE_PROMPT = (
    'You are the Relevance specialist. '
    'Evaluate RELEVANCE only. '
    'Assume the identified premise is provisionally acceptable. '
    'Ask whether that premise actually counts as a reason bearing '
    'on the conclusion. '
    'Identify a relevance gap only when the stated reason fails '
    'to materially support the target conclusion. '
    'Do not decide whether the premise is true. '
    'Do not decide whether the total amount of support is sufficient. '
    'Do not classify the argument. '
)


SUFFICIENCY_PROMPT = (
    'You are the Sufficiency specialist. '
    'Evaluate SUFFICIENCY only. '
    'Assume the identified premises are provisionally acceptable '
    'and relevant. '
    'Ask whether their combined support is enough for a conclusion '
    'of this strength and scope. '
    'Inspect missing warrants, scope jumps, case-to-group moves, '
    'unsupported consequence chains and claims that alternatives '
    'are exhaustive. '
    'Describe the structural gap without naming a task class. '
    'Do not classify the argument. '
)


COCOLOFA_RULES = (
    'Appeal to Authority: treating an inappropriate authority '
    'as sufficient proof. '
    'Appeal to Majority: treating popularity as proof of truth '
    'or correctness. '
    'Appeal to Nature: treating naturalness alone as proof of '
    'goodness or correctness. '
    'Appeal to Tradition: treating longstanding practice alone '
    'as justification. '
    'Appeal to Worse Problems: dismissing an issue solely because '
    'worse problems exist. '
    'False Dilemma: improperly restricting available alternatives. '
    'Hasty Generalization: drawing a broad conclusion from '
    'insufficient or unrepresentative cases. '
    'Slippery Slope: asserting an inadequately supported progression '
    'of consequences. '
)


ROLE_PROMPTS = {
    'ARSArgumentDecomposer': DECOMPOSER_PROMPT,
    'Acceptability': ACCEPTABILITY_PROMPT,
    'Relevance': RELEVANCE_PROMPT,
    'Sufficiency': SUFFICIENCY_PROMPT,
}


def ars_system_prompt(role, task):
    if role in ROLE_PROMPTS:
        return ARS_COMMON + ROLE_PROMPTS[role]

    if role != 'ARSArbiter':
        raise ValueError(f'Unknown ARS role: {role}')

    if task == 'detection':
        task_instruction = (
            'You are the only label-aware component. '
            'Determine whether TARGET instantiates one of the '
            'eight closed-set CoCoLoFa classes. '
            'If no class is established, output Non-Fallacious. '
        )
    elif task == 'classification':
        task_instruction = (
            'You are the only label-aware component. '
            'TARGET is known to contain one of the eight '
            'closed-set CoCoLoFa classes. '
            'Choose exactly one class. '
        )
    else:
        raise ValueError(f'Unknown task: {task}')

    return (
        'Use only the supplied raw text, decomposition and '
        'FINAL ARS diagnoses. '
        'Specialist reports are hypotheses, not votes or facts. '
        'Re-check every decisive specialist claim against TARGET. '
        'Do not reward verbosity, confidence or repeated claims. '
        + task_instruction
        + COCOLOFA_RULES
        + 'Allowed final task labels: '
        + ', '.join(labels_for(task))
        + '. '
        'Map ARS diagnoses to the benchmark ontology only after '
        'validating argument structure. '
        'Identify the nearest competing class and explain why '
        'the decisive structure fits one better than the other. '
        'Return only JSON matching the provided schema. '
    )
