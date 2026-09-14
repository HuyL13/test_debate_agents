FALLACIES = (
    'Appeal to Authority', 'Appeal to Majority', 'Appeal to Nature',
    'Appeal to Tradition', 'Appeal to Worse Problems', 'False Dilemma',
    'Hasty Generalization', 'Slippery Slope',
)
DETECTION = ('Non-Fallacious', 'Fallacious')
ANALYSTS = ('scheme', 'enthymeme', 'critical')


def labels_for(task):
    if task == 'detection':
        return DETECTION
    if task == 'classification':
        return FALLACIES
    raise ValueError(f'Unknown task: {task}')
