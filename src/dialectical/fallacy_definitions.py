"""ArgMining 2026 LLM-Extracted Fallacy Patterns mapped to CoCoLoFa 8 Classes.

Based on the empirical findings from 'Beyond Logical Forms: LLM-Extracted Patterns for
Fallacy Classification' (ArgMining 2026), incorporating abstract logical forms,
reasoning defect mechanisms, and syntactic markers into system prompts.
"""

from typing import Dict, List, NamedTuple


class FallacyPattern(NamedTuple):
    name: str
    core_definition: str
    logical_form: str
    reasoning_defect: str
    syntactic_markers: List[str]
    boundary_constraint: str


COCOLOFA_PATTERNS: Dict[str, FallacyPattern] = {
    'Appeal to Authority': FallacyPattern(
        name='Appeal to Authority',
        core_definition='Treating an inappropriate, unqualified, or non-domain authority as sufficient proof of a claim.',
        logical_form='Person/Source P asserts claim C -> Therefore C is true (without domain-relevant empirical justification).',
        reasoning_defect='Authority, status, prestige, or titles are substituted for demonstrable evidence or valid reasoning.',
        syntactic_markers=[
            'According to [expert/celebrity/title]...',
            'Listen to the experts instead of questioning...',
            'Dr./Professor X said that...',
            'Citing prestige or official status as the sole verification.'
        ],
        boundary_constraint=(
            'Citing a qualified expert accompanied by relevant factual consensus is NOT fallacious. '
            'Must involve treating authority alone as substitute for argument.'
        )
    ),
    'Appeal to Majority': FallacyPattern(
        name='Appeal to Majority',
        core_definition='Treating popularity, prevalence, or widespread belief as proof of truth or correctness.',
        logical_form='Group G (everyone, majority, X% of people) believes/endorses claim C -> Therefore C is valid/true.',
        reasoning_defect='Widespread acceptance or democratic consensus is conflated with epistemic validity or moral correctness.',
        syntactic_markers=[
            'Everyone knows that...',
            'Most people agree that...',
            '51% of people believe...',
            "It can't be that the entire world is wrong...",
            'No one believes that anymore...',
            'Appealing to popular vote or consensus as factual proof.'
        ],
        boundary_constraint=(
            'Describing public opinion as an empirical demographic fact is NOT fallacious. '
            'It is fallacious only when popularity is used to prove the truth of the proposition itself.'
        )
    ),
    'Appeal to Nature': FallacyPattern(
        name='Appeal to Nature',
        core_definition='Treating naturalness alone as proof of goodness or correctness, or synthetic/unnatural as inherently bad.',
        logical_form='X is natural -> Therefore X is good/safe/healthy; or Y is artificial/unnatural -> Therefore Y is bad/harmful.',
        reasoning_defect='Directly derives normative value or empirical safety solely from whether something occurs in nature.',
        syntactic_markers=[
            "It's all-natural, so it's completely safe/healthy...",
            'Unnatural chemicals / against nature...',
            'Nature intended it this way...',
            'Equating artificial or processed with inherently destructive or immoral.'
        ],
        boundary_constraint=(
            'Citing specific empirical, biological, or chemical evidence about an ingredient is NOT fallacious. '
            'Must derive correctness or safety solely from the property of being natural.'
        )
    ),
    'Appeal to Tradition': FallacyPattern(
        name='Appeal to Tradition',
        core_definition='Treating longstanding practice, custom, or historical longevity alone as justification for truth or validity.',
        logical_form='Practice/Belief X has been done for a long time / is traditional -> Therefore X is correct, optimal, or right.',
        reasoning_defect='Chronological duration or historical precedent is substituted for functional merit or logical justification.',
        syntactic_markers=[
            "We have always done it this way...",
            'Time-tested tradition proves...',
            'Centuries of custom dictate that...',
            'Traditional values must be maintained because of history.'
        ],
        boundary_constraint=(
            'Valuing historical or cultural heritage sentimentally is NOT fallacious. '
            'It is fallacious only when historical longevity is treated as logical proof of validity or correctness.'
        )
    ),
    'Appeal to Worse Problems': FallacyPattern(
        name='Appeal to Worse Problems',
        core_definition='Dismissing an issue or argument solely because worse or larger problems exist elsewhere (relative privation).',
        logical_form='Issue X is raised; Separate Problem Y exists where Severity(Y) > Severity(X) -> Therefore dismiss/ignore X.',
        reasoning_defect='Deflects from analyzing the validity or merit of X by introducing a more severe, unrelated external problem.',
        syntactic_markers=[
            'Why are we worrying about X when people are dying of Y?',
            'There are far worse problems in the world than X...',
            'First solve Y before complaining about X...',
            'What about [greater external catastrophe]?'
        ],
        boundary_constraint=(
            'STRICT REQUIREMENT: Requires an explicit, distinct, external problem Y (a separate crisis, issue, or group) '
            'brought in to minimize or dismiss topic X. If the text merely warns that topic X itself will get worse, '
            'or describes how bad topic X is, it is NOT Appeal to Worse Problems (evaluate as Slippery Slope or relevant class).'
        )
    ),
    'False Dilemma': FallacyPattern(
        name='False Dilemma',
        core_definition='Improperly restricting available alternatives to two polar extremes while ignoring intermediate options.',
        logical_form='Premise: Either A or B (A OR B; NOT A -> B), falsely asserting exhaustiveness -> Therefore choose A or B.',
        reasoning_defect='Artificially compresses a complex, continuous, or multi-option spectrum into a binary forced choice.',
        syntactic_markers=[
            'Either A or B, there is no other way...',
            "You're either with us or against us...",
            'Pick a side / you must choose between X and Y...',
            'The only alternative to X is total Y...',
            'No middle ground.'
        ],
        boundary_constraint=(
            'Genuine exhaustive logical or physical dichotomies (e.g. alive vs dead, even vs odd) are NOT fallacious. '
            'Requires an explicit or implicit exhaustiveness commitment that ignores realistic alternatives.'
        )
    ),
    'Hasty Generalization': FallacyPattern(
        name='Hasty Generalization',
        core_definition='Drawing a broad, universal, or population-wide conclusion from an unrepresentative or anecdotal sample.',
        logical_form='Limited/anecdotal subset S (subset of A) exhibits property P -> Therefore all A exhibits property P.',
        reasoning_defect='Inductive leap across population boundaries based on negligible, biased, or single-case sample evidence.',
        syntactic_markers=[
            'I know someone who... therefore all of them...',
            'In my personal experience, so it always happens...',
            'I saw one instance, which proves everyone...',
            'Universal quantifiers (always, never, everyone, nobody) derived from anecdotes.'
        ],
        boundary_constraint=(
            'Must involve a sample-to-population inductive leap. A broad general opinion, subjective complaint, or consequence '
            'prediction without inductive movement from sample cases is NOT Hasty Generalization. Distinguish from Slippery Slope.'
        )
    ),
    'Slippery Slope': FallacyPattern(
        name='Slippery Slope',
        core_definition='Asserting that an action, policy, or event will inevitably initiate or escalate into severe negative consequences, deterioration, or extreme outcomes without causal justification.',
        logical_form='A occurs -> Inevitable negative deterioration or escalation (B, or B -> ... -> Z) without sufficient causal warrants.',
        reasoning_defect='Treats contingent negative consequences or downward trajectories as inevitable without justifying why the negative leap will necessarily occur.',
        syntactic_markers=[
            'If we allow A, next will be B, and eventually Z...',
            'A dangerous precedent / opens the floodgates / can lead to...',
            'Where does it end? / What is next? / Who else is next?',
            'Things will only get worse / things just get bad / if nothing is done / otherwise...'
        ],
        boundary_constraint=(
            'Includes multi-step domino chains as well as single-step unjustified leaps to severe negative outcomes ("can lead to..."), '
            'downward deterioration trends ("only get worse", "things just get bad"), or rhetorical boundary questions ("who else / what next?"). '
            'Distinguish from Appeal to Worse Problems: Slippery Slope warns about the deteriorating outcomes of topic A itself, '
            'rather than introducing a separate, external problem B.'
        )
    ),
}


def get_pattern_enriched_definitions() -> str:
    """Return enriched definitions with abstract logical forms and syntactic markers."""
    lines = []
    for fp in COCOLOFA_PATTERNS.values():
        markers_str = ' | '.join(fp.syntactic_markers[:3])
        lines.append(
            f"[{fp.name}]: {fp.core_definition} "
            f"Logical Form: {fp.logical_form} "
            f"Typical Markers: \"{markers_str}\". "
            f"Constraint: {fp.boundary_constraint}"
        )
    # Comparative summary constraints
    lines.append(
        "CRITICAL DISCRIMINATION RULES: "
        "(1) Distinguish negative consequence escalation or downward deterioration (Slippery Slope: action A leads to worse outcome / deterioration of topic A) from "
        "sample-to-population inductive generalization (Hasty Generalization: sample S (subset of A) -> all A). "
        "Slippery Slope warns about the trajectory of topic A itself; Appeal to Worse Problems strictly requires deflecting to a distinct, separate external problem B. "
        "(2) False Dilemma strictly requires an exhaustiveness commitment eliminating viable third options. "
        "(3) Appeals (Authority, Majority, Nature, Tradition, Worse Problems) require that the cited property "
        "does justificatory work as the sole proof, rather than being an incidental mention or background context."
    )
    return " ".join(lines)
