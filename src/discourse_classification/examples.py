"""Small, manually annotated role demonstrations from the training split only.

No fallacy labels are supplied to the extractor. These illustrate attribution,
compressed consequences and a focal-to-systemic issue comparison.
"""
from copy import deepcopy


def _quote(text, role):
    return {'source': 'comment', 'text': text, 'role': role}


EXAMPLES = [
    {
        'train_sample_id': '597:8988',
        'comment': 'This is the right thing to do. I know that because the government approved the debates and the government is always right.',
        'output': {'arguments': [{
            'kind': 'SOURCE_JUSTIFICATION', 'basis': 'AUTHORITY', 'stance': 'USES', 'relation_status': 'EXPLICIT',
            'evidence': [_quote('the government approved the debates', 'BASIS'), _quote('This is the right thing to do', 'CLAIM')],
        }]},
    },
    {
        'train_sample_id': '35:3252',
        'comment': 'It appears that the majority of the people are calling for reform. We need to give the people what they want. Shouldn\'t the majority know what society wants. the majority of the public agreeing can only lead to improvement. This needs to be thoughtfully executed in order to ensure the best results. We need to approach this in a democratic fashion as this is in the best interest of society.',
        'output': {'arguments': [{
            'kind': 'SOURCE_JUSTIFICATION', 'basis': 'POPULARITY', 'stance': 'USES', 'relation_status': 'IMPLICIT',
            'evidence': [_quote('the majority of the people are calling for reform', 'BASIS'),
                         _quote('We need to give the people what they want', 'CLAIM')],
        }]},
    },
    {
        'train_sample_id': '357:7067',
        'comment': "It's natural for bad leaders to lie. So the death toll in Nicaragua will be manipulated. More protests would do the people good. They need to push them out.",
        'output': {'arguments': [{
            'kind': 'SOURCE_JUSTIFICATION', 'basis': 'NATURE', 'stance': 'USES', 'relation_status': 'EXPLICIT',
            'evidence': [_quote("It's natural for bad leaders to lie", 'BASIS'),
                         _quote('the death toll in Nicaragua will be manipulated', 'CLAIM')],
        }]},
    },
    {
        'train_sample_id': '357:7068',
        'comment': 'Imagine how bad the situation has to be for this many people to flee and try to basically engage in revolution in exile. I bet the entire population still there is wishing they could leave too. Sounds like life under this government is virtually like being in prison.',
        'output': {'arguments': [{
            'kind': 'GENERALIZATION', 'stance': 'USES', 'relation_status': 'IMPLICIT',
            'evidence': [_quote('this many people to flee', 'SAMPLE'), _quote('the entire population still there', 'POPULATION'),
                         _quote('the entire population still there is wishing they could leave too', 'CONCLUSION')],
        }]},
    },
    {
        'train_sample_id': '357:5869',
        'comment': "So those fleeing are just choosing to not help their people? You can't complain about oppression and then leave your people. Either stay and help or leave and stop complaining about what's going on as its no longer your problem. You can't act like you care about your people and then just up and leave!",
        'output': {'arguments': [{
            'kind': 'CHOICE', 'exhaustivity': 'EXHAUSTIVE', 'stance': 'USES', 'relation_status': 'EXPLICIT',
            'evidence': [_quote('stay and help', 'ALTERNATIVE'), _quote('leave and stop complaining', 'ALTERNATIVE')],
        }]},
    },
    {
        'train_sample_id': '459:7374',
        'comment': 'Philipino president Duarte is not acting on violence as strongly as he should. People seem to think the violence is spiking under his presidency. And if the violence is so high, why are we only focused on one coffee shop killing? Let\'s focus on all of the killings in general. I would like to see an article on how many killings there have been under Duarte and the consequences for the perpetrators.',
        'output': {'arguments': [{
            'kind': 'ISSUE_COMPARISON', 'use': 'PRIORITIZE', 'severity': 'BROADER',
            'stance': 'USES', 'relation_status': 'EXPLICIT',
            'evidence': [_quote('one coffee shop killing', 'FOCAL_ISSUE'),
                         _quote('all of the killings in general', 'COMPARISON_ISSUE'),
                         _quote("Let's focus on all of the killings in general", 'CLAIM')],
        }]},
    },
    {
        'train_sample_id': '327:5779',
        'comment': "Tradition does dictate that widespread sentiment should shape decisions; it's been our approach for generations, hasn't it? However, aren't there instances when popular opinion didn't necessarily point us towards the best course of action? History has its fair share of mistakes made due to popular sentiment alone. We've grown so much as a society since then and it may be worth reevaluating if every traditional approach still holds up to scrutiny. Remember, tradition is important but also remember that it's okay to question age-old practices when forging our future.",
        'output': {'arguments': [{
            'kind': 'SOURCE_JUSTIFICATION', 'basis': 'HISTORY',
            'stance': 'CRITICIZES', 'relation_status': 'EXPLICIT',
            'evidence': [_quote("it's been our approach for generations", 'BASIS'),
                         _quote('widespread sentiment should shape decisions', 'CLAIM')],
        }]},
    },
    {
        'train_sample_id': '159:4673',
        'comment': 'Turkey is a democracy but if it keeps going in this direction it will make a decline into a dictatorship. If one party gains all the control over the voting process, there will be no turning back. This will lead to religious freedoms being completely taken away.',
        'output': {'arguments': [{
            'kind': 'CONSEQUENCE', 'progression': 'ADVERSE',
            'stance': 'USES', 'relation_status': 'EXPLICIT',
            'evidence': [_quote('one party gains all the control over the voting process', 'ACTION'),
                         _quote('religious freedoms being completely taken away', 'OUTCOME')],
        }]},
    },
    {
        'train_sample_id': '449:6143',
        'comment': "It is important for LGBTQ+ to have their representation in the census reports. I can't help but think about how easy is was for the government to just pass a rule then decide not to do it. Where is the outcry for that happening in the government? That was done too easily to me and makes me wonder what could happen if they kept doing that? This problem is just a small part of the larger one we face with the absence of transparency and checks and balances with our government. Just think about the pressing issues that might have been silently passed or ignored due to such behavior. If they can take back a decision as massively important as this one, who knows what other policies they might retract without us knowing! At the end of the day, it's not just about the LGBTQ+ representation but about the pivotal control the government has over us all.",
        'output': {'arguments': [{
            'kind': 'ISSUE_COMPARISON', 'use': 'PRIORITIZE', 'severity': 'HIGHER',
            'stance': 'USES', 'relation_status': 'EXPLICIT',
            'evidence': [_quote('LGBTQ+ representation', 'FOCAL_ISSUE'),
                         _quote('the pivotal control the government has over us all', 'COMPARISON_ISSUE'),
                         _quote("it's not just about the LGBTQ+ representation but about the pivotal control the government has over us all", 'CLAIM')],
        }]},
    },
]


def role_examples(excluded_articles=()):
    excluded = {str(article) for article in excluded_articles}
    return deepcopy([ex for ex in EXAMPLES if ex['train_sample_id'].split(':')[0] not in excluded])
