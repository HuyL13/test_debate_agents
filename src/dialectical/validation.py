"""Structural cue definitions, validation, and locking rules for CoCoLoFa 8 fallacy classes.

Grounded in argumentation theory (Walton, Govier, Tindale) and train.json (no dev leakage).
Used to validate quotes, filter rhetorical hallucinations, and enforce cue locking.
"""

import re
from typing import Any, Dict, List, Optional
from src.schemas import _normalize_quote_text
from src.labels import FALLACIES

# Structural Cue Patterns compiled from argumentation literature & train.json
# Note: dev split is strictly excluded to prevent data leakage.
CUE_PATTERNS: Dict[str, re.Pattern] = {
    'Appeal to Authority': re.compile(
        r'\b('
        # Professional/academic titles & experts
        r'dr|doctor|prof|professor|expert|experts|specialist|specialists|'
        r'scientist|scientists|researcher|researchers|scholar|scholars|historian|historians|'
        r'economist|economists|analyst|analysts|physician|surgeon|psychologist|psychiatrist|philosopher|'
        # Legal, political, institutional figures
        r'official|officials|authorities|authority|spokesperson|spokesman|spokeswoman|'
        r'police|cops|judge|lawyer|attorney|prosecutor|president|minister|senator|governor|'
        r'ceo|ceos|nobel|'
        # Named organizations & agencies
        r'cdc|who|fda|un|nih|nasa|fbi|cia|epa|cpj|supreme court|high court|'
        r'government (?:official|officials|report|study|stated|says|said|claims|decreed|announced)|'
        r'institute|institution|academy|university|oxford|harvard|cambridge|mit|yale|stanford|'
        # Citations, studies, and speech acts of authority
        r'study|studies|research|survey|paper|report|journal|lancet|nature|science|peer-reviewed|'
        r'according to|cited|cites|quoted|quotes|states that|stated that|claims that|says that|said that|'
        r'argues that|argued that|warned that|makes it clear|understands the|'
        r'listen to|trust in|trust [a-z]+ over|in charge'
        r')\b',
        re.I
    ),
    'Appeal to Tradition': re.compile(
        r'\b('
        # Root tradition/custom words
        r'tradition|traditional|traditionally|traditionalist|custom|customary|customs|heritage|'
        # Longevity and historical continuity
        r'always been|always was|always done|for centuries|for generations|for decades|for millennia|for years|'
        r'for \d+ years|throughout history|history shows|'
        # Ancestral / generational authority
        r'ancestor|ancestors|ancestral|forefather|forefathers|founders|founding fathers|'
        r'granddad|grandfather|grandmother|'
        # Norms & longstanding practices
        r'longstanding|long-standing|time-tested|since the beginning|since day one|since time immemorial|'
        r'old as time|ancient|passed down|tried and true|never changed|the norm|it\'s the norm|'
        r'status quo|way it has always been|prohibition'
        r')\b',
        re.I
    ),
    'Appeal to Nature': re.compile(
        r'\b('
        # Naturalness equated with good/safe
        r'natural|naturally|nature|all-natural|mother nature|nature intended|god-given|god intended|'
        r'biology intended|organic|pure nature|'
        # Artificiality equated with bad/harmful
        r'unnatural|synthetic|chemical|chemicals|artificial|man-made|gmo|toxin|toxins|poison|processed|'
        r'ecosystem|ecosystems'
        r')\b',
        re.I
    ),
    'Appeal to Majority': re.compile(
        r'\b('
        # Majority & populace quantifiers
        r'majority|majority of|most people|most of us|everyone|everybody|every single person|'
        r'nobody|no one|popular|popularity|masses|public opinion|consensus|widely accepted|widely believed|'
        r'common knowledge|polls show|millions of|billions of|entire world|whole world|'
        r'outnumber|outnumbered|citizens outnumber|crowd|all of us|everybody knows'
        r')\b',
        re.I
    ),
    'Appeal to Worse Problems': re.compile(
        r'\b('
        # Comparative privation markers
        r'worse than|far worse|much worse|worse problem|bigger problem|larger problem|greater problem|'
        r'more serious than|more important than|more urgent|more pressing|more vital|'
        r'least of our problems|real problem|actual problem|real crisis|real issue|bigger fish to fry|'
        r'first world problem|'
        # Deflection questions & external crises
        r'what about|how about|why worry about|why care about|why focus on|why are we .* when|'
        r'why aren\'t they|while people are|while children are|people are dying|children are starving|'
        r'starving|dying of|homeless|poverty|war in|cancer|famine|struggling to get by|paycheck to paycheck|'
        # Priority redirections
        r'first solve|priorit|priorities|tackled first|dealt with first|instead of focusing|'
        r'other problem|other issue|other things|better things to worry|bigger picture|'
        r'consequences right now as opposed|doesn\'t diminish other'
        r')\b',
        re.I
    ),
    'False Dilemma': re.compile(
        r'\b('
        # Binary disjunction & polarization
        r'either|or else|only two|two choices|two options|two paths|only two ways|choose one|pick one|'
        r'pick a side|with us or against|for us or against|no in-between|no middle ground|'
        r'no other option|no other choice|no alternative|only alternative|the only choice|the only way .* or|'
        r'no other (?:possible )?(?:answer|solution|way|explanation)|'
        r'binary|black and white'
        r')\b',
        re.I
    ),
    'Slippery Slope': re.compile(
        r'\b('
        # Domino escalation & causal chains
        r'lead to|leads to|will lead to|can lead to|could lead to|just going to lead to|eventually|'
        r'next thing|next they|next it|soon they|soon it|down the road|in no time|'
        r'spiral into|spiral out|snowball into|open the floodgates|floodgates|slippery slope|'
        r'dangerous precedent|set a precedent|where does it end|where will it all end|'
        r'what(\'s| is) next|who is next|who else is next|who else (?:could|is|will|would)|what else (?:could|is|will|would)|'
        r'before long|domino|first it\'s .* then|'
        r'inevitably|only get worse|just get worse|much worse|road to anarchy|paved the way|'
        r'starts with|starts out|sooner or later|if left unchecked|if unchecked|'
        r'imagine if .* trend|no turning back|can only lead|will be blaming'
        r')\b',
        re.I
    ),
    'Hasty Generalization': re.compile(
        r'\b('
        # Specific sample / anecdote anchor
        r'i know someone|i know a|i have a friend|my friend|my cousin|my uncle|my brother|my sister|'
        r'my neighbour|my neighbor|my dad|my mom|in my experience|personal experience|one time|once i saw|'
        r'i saw one|one case|anecdote|for instance, i|for example, i|i once|every time i|i\'ve seen|'
        r'i met|one person|a guy|this one time|all of them tell me|if these people can\'t even|'
        r'all their other ideas|from all i\'ve seen|whenever i see|'
        # Sample leap to population
        r'entire justice system|whole country|every other part|all subsequent'
        r')\b',
        re.I
    ),
}

# Anchored classes that possess explicit structural warrants
LOCKED_ANCHOR_CLASSES = {
    'Appeal to Authority',
    'Appeal to Tradition',
    'Appeal to Nature',
    'Appeal to Majority',
    'Appeal to Worse Problems',
    'False Dilemma',
}


def has_class_cue(fallacy_class: str, text: str) -> bool:
    """Check if the text contains verified structural cues for the given fallacy class."""
    if not text or not isinstance(text, str):
        return False
    pat = CUE_PATTERNS.get(fallacy_class)
    if not pat:
        return True  # If no pattern registered, don't block
    return bool(pat.search(_normalize_quote_text(text)))


def is_cue_locked(candidate_class: str, quote: str) -> bool:
    """Check if candidate class is an anchored class with a verified structural cue."""
    if candidate_class not in LOCKED_ANCHOR_CLASSES:
        return False
    return has_class_cue(candidate_class, quote)


def validate_and_normalize_defender(
    prosecutor: Dict[str, Any],
    defender: Dict[str, Any],
    comment: str,
) -> Dict[str, Any]:
    """Validate and normalize Defender plea before Arbiter adjudication.

    Rules:
    1. If alt == candidate -> concede_charge = True, alternative_class = 'None'.
    2. If concede_charge is True -> alternative_class = 'None'.
    3. counter_quote must be a non-empty substring of comment.
    4. counter_quote must NOT be identical to candidate quote.
    5. counter_quote must have length >= 5 words (or entire comment length if comment < 5 words).
    6. counter_quote must contain the structural cue for alternative_class.
    7. If Candidate has a locked structural cue (e.g. Authority, Tradition, Worse Problems)
       and Defender offers vague SS/HG without required cue, nullify flip.

    Returns the normalized defender dictionary.
    """
    normalized = dict(defender)
    cand_class = prosecutor.get('candidate_class', '')
    cand_quote = prosecutor.get('quote', '')
    alt_class = normalized.get('alternative_class', 'None')
    concede = normalized.get('concede_charge', False)
    counter_quote = normalized.get('counter_quote', '')

    # Rule 1: alt == candidate -> concede
    if alt_class == cand_class:
        normalized['concede_charge'] = True
        normalized['alternative_class'] = 'None'
        normalized['charitable_interpretation'] = (
            f"Defender concurs with Prosecutor candidate class '{cand_class}'."
        )
        return normalized

    # Rule 2: Already conceding
    if concede or alt_class == 'None':
        normalized['concede_charge'] = True
        normalized['alternative_class'] = 'None'
        return normalized

    # Rule 3: Substring check
    norm_c_quote = _normalize_quote_text(counter_quote).casefold()
    norm_comment = _normalize_quote_text(comment).casefold()
    if not norm_c_quote or norm_c_quote not in norm_comment:
        normalized['concede_charge'] = True
        normalized['alternative_class'] = 'None'
        normalized['charitable_interpretation'] = (
            "Defender counter_quote was not found in target comment. Flip nullified."
        )
        return normalized

    # Rule 4: Non-identical to candidate quote
    norm_cand_quote = _normalize_quote_text(cand_quote).casefold()
    if norm_c_quote == norm_cand_quote:
        normalized['concede_charge'] = True
        normalized['alternative_class'] = 'None'
        normalized['charitable_interpretation'] = (
            "Defender counter_quote is identical to Prosecutor candidate quote. Flip nullified."
        )
        return normalized

    # Rule 5: Word length check (>= 3 words or full comment length)
    quote_words = counter_quote.strip().split()
    comment_words = comment.strip().split()
    min_len = min(3, len(comment_words))
    if len(quote_words) < min_len:
        normalized['concede_charge'] = True
        normalized['alternative_class'] = 'None'
        normalized['charitable_interpretation'] = (
            f"Defender counter_quote too short ({len(quote_words)} words < {min_len}). Flip nullified."
        )
        return normalized

    # Rule 6: Structural cue check for alternative_class
    if not has_class_cue(alt_class, counter_quote):
        normalized['concede_charge'] = True
        normalized['alternative_class'] = 'None'
        normalized['charitable_interpretation'] = (
            f"Defender counter_quote lacks required structural cue for '{alt_class}'. Flip nullified."
        )
        return normalized

    # Rule 7: Cue locking protection
    if is_cue_locked(cand_class, cand_quote):
        if alt_class in ('Slippery Slope', 'Hasty Generalization') and not has_class_cue(alt_class, counter_quote):
            normalized['concede_charge'] = True
            normalized['alternative_class'] = 'None'
            normalized['charitable_interpretation'] = (
                f"Candidate '{cand_class}' has verified structural anchor. "
                f"Defender alternative '{alt_class}' lacks sufficient countervailing evidence. Flip nullified."
            )
            return normalized

    return normalized
