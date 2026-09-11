from src.labels import labels_for


def vector(report, task):
    """Detection signed confidence; classification a categorical confidence vector."""
    if 'confidence' not in report:
        return [int(report['prediction'] == label) for label in labels_for(task)]
    if task == 'detection':
        return [report['confidence'] * (1 if report['prediction'] == 'Fallacious' else -1)]
    # One-hot mass plus uniform residual uncertainty, with no ordinal label distance.
    labels = labels_for(task)
    residual = (1 - report['confidence']) / len(labels)
    return [residual + (report['confidence'] if label == report['prediction'] else 0) for label in labels]


def distance(a, b, task):
    x, y = vector(a, task), vector(b, task)
    return sum(abs(i - j) for i, j in zip(x, y)) / (1 if task == 'detection' else 2)


def stable(current, previous, roles, task):
    return sum(distance(current[r], previous[r], task) for r in roles) / len(roles) < 0.05


def team_gap(reports, affirmative, negative, task):
    def mean(roles):
        vectors = [vector(reports[r], task) for r in roles]
        return [sum(xs) / len(xs) for xs in zip(*vectors)]
    return sum(abs(a - b) for a, b in zip(mean(affirmative), mean(negative))) / (1 if task == 'detection' else 2)
