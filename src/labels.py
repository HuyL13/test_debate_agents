FALLACIES = (
    'Appeal to Authority', 'Appeal to Majority', 'Appeal to Nature',
    'Appeal to Tradition', 'Appeal to Worse Problems', 'False Dilemma',
    'Hasty Generalization', 'Slippery Slope',
)
DETECTION = ('Non-Fallacious', 'Fallacious')
ROLES = ('Factual', 'Logical', 'Contextual')
DIAGNOSTIC_ROLES = ('Inference', 'Evidence', 'SemanticContext')
ARS_ROLES = (
    'Acceptability',
    'Relevance',
    'Sufficiency',
)

ARS_SPECIAL_ROLES = (
    'ARSArgumentDecomposer',
    'ARSArbiter',
)
PROTOCOLS = ('round_robin', 'point_counterpoint', 'cross_examination')

def labels_for(task):
    if task == 'detection':
        return DETECTION
    if task == 'classification':
        return FALLACIES
    raise ValueError(f'Unknown task: {task}')


FALLACY_ALIASES = {
    'appeal to consequence': 'Appeal to Worse Problems',
    'appeal to consequences': 'Appeal to Worse Problems',
    'argument from consequences': 'Appeal to Worse Problems',
    'appeal to emotion': 'Appeal to Worse Problems',
    'appeal to pity': 'Appeal to Worse Problems',
    'appeal to sympathy': 'Appeal to Worse Problems',
    'appeal to empathy': 'Appeal to Worse Problems',
    'appeal to compassion': 'Appeal to Worse Problems',
    'argumentum ad misericordiam': 'Appeal to Worse Problems',
    'ad misericordiam': 'Appeal to Worse Problems',
    'appeal to guilt': 'Appeal to Worse Problems',
    'appeal to fear': 'Slippery Slope',
    'appeal to force': 'Appeal to Worse Problems',
    'appeal to ridicule': 'Appeal to Worse Problems',
    'appeal to spite': 'Appeal to Worse Problems',
    'appeal to popularity': 'Appeal to Majority',
    'bandwagon': 'Appeal to Majority',
    'ad populum': 'Appeal to Majority',
    'appeal to common belief': 'Appeal to Majority',
    'consensus gentium': 'Appeal to Majority',
    'appeal to antiquity': 'Appeal to Tradition',
    'appeal to common practice': 'Appeal to Tradition',
    'appeal to age': 'Appeal to Tradition',
    'appeal to nature': 'Appeal to Nature',
    'naturalistic fallacy': 'Appeal to Nature',
    'ad verecundiam': 'Appeal to Authority',
    'appeal to expert': 'Appeal to Authority',
    'false dichotomy': 'False Dilemma',
    'black and white': 'False Dilemma',
    'either or': 'False Dilemma',
    'false equivalence': 'False Dilemma',
    'bifurcation': 'False Dilemma',
    'overgeneralization': 'Hasty Generalization',
    'jumping to conclusions': 'Hasty Generalization',
    'faulty generalization': 'Hasty Generalization',
    'anecdotal evidence': 'Hasty Generalization',
    'faulty analogy': 'Hasty Generalization',
    'post hoc': 'Hasty Generalization',
    'cum hoc': 'Hasty Generalization',
    'red herring': 'Appeal to Worse Problems',
    'whataboutism': 'Appeal to Worse Problems',
    'straw man': 'Appeal to Worse Problems',
    'ad hominem': 'Appeal to Worse Problems',
    'two wrongs make a right': 'Appeal to Worse Problems',
    'circular reasoning': 'Appeal to Worse Problems',
    'begging the question': 'Appeal to Worse Problems',
    'slippery slope': 'Slippery Slope',
    'domino fallacy': 'Slippery Slope',
}


def normalize_fallacy_name(name, default=None):
    if not isinstance(name, str):
        return default
    s = name.strip()
    for f in FALLACIES:
        if f.casefold() == s.casefold():
            return f
    return FALLACY_ALIASES.get(s.casefold(), default)
