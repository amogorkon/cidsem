import re
from typing import List, Tuple

# Very small, rule-based SPO extractor for prototyping.
# Input: sentence string
# Output: list of (subject, predicate, object) tuples as simple phrases

_NOUN_RE = re.compile(r"\b([A-Z][a-zA-Z]*(?:\s+[A-Z][a-zA-Z]*)*)\b")

# Ordered verb patterns (longer/more specific first) mapped to normalized predicate
_VERB_PATTERNS = [
    ("was hired", "hired"),
    ("is hired", "hired"),
    ("joined", "joined"),
    ("was located", "located at"),
    ("located at", "located at"),
    ("was", "be"),
    ("is", "be"),
    ("are", "be"),
    ("were", "be"),
    ("left", "left"),
    ("hired", "hired"),
    ("works as", "works as"),
    ("works", "works as"),
    ("work", "works as"),
    ("became", "became"),
]


def extract_spo(sentence: str) -> List[Tuple[str, str, str]]:
    s = sentence.strip()
    if not s:
        return []

    lower = s.lower()

    # find best verb pattern in order (record index)
    verb = None
    after = ""
    verb_idx = -1
    for pattern, norm in _VERB_PATTERNS:
        idx = lower.find(pattern)
        if idx != -1:
            verb = norm
            after = s[idx + len(pattern) :]
            verb_idx = idx
            break

    if not verb:
        return []

    # find all capitalized noun-like phrases
    noun_matches = [(m.start(), m.group(1)) for m in _NOUN_RE.finditer(s)]

    # choose subject as the capitalized noun closest before the verb index
    subject = ""
    subject_start = -1
    if noun_matches:
        candidates = [
            (st, g) for (st, g) in noun_matches if st < verb_idx and len(g) > 1
        ]
        if candidates:
            subject_start, subject = sorted(candidates, key=lambda x: x[0])[-1]
        else:
            # fallback: first reasonable noun
            for st, g in noun_matches:
                if g.lower() not in ("in", "the", "once", "qwerty") and len(g) > 1:
                    subject_start, subject = st, g
                    break
            if not subject:
                subject_start, subject = noun_matches[0]

    # simple pronoun resolution: if subject is a pronoun, prefer nearest preceding proper noun
    pronouns = {"he", "she", "they", "we", "i", "you", "it"}
    if subject and subject.strip().lower() in pronouns:
        # find last noun before subject_start that's not a pronoun
        prior = [
            (st, g)
            for (st, g) in noun_matches
            if st < subject_start and g.strip().lower() not in pronouns
        ]
        if prior:
            # prefer single-token names (likely persons) over multi-word locations
            single_token = [p for p in prior if " " not in p[1].strip()]
            if single_token:
                subject_start, subject = sorted(single_token, key=lambda x: x[0])[-1]
            else:
                subject_start, subject = sorted(prior, key=lambda x: x[0])[-1]

    # pick object as first capitalized or remaining phrase
    # prefer organization names after prepositions like 'at', 'for', 'with'
    # prefer an immediate capitalized noun right after the verb
    after_stripped = after.lstrip()
    start_match = _NOUN_RE.match(after_stripped)
    if start_match:
        obj = start_match.group(1)
    else:
        # prefer organization names after prepositions like 'at', 'for', 'with' (exclude 'as' to avoid roles)
        PREP_ORG_RE = re.compile(
            r"\b(?:at|for|with|from|to|in|by)\s+([A-Z][A-Za-z0-9][\w\-']*(?:\s+[A-Z][A-Za-z0-9][\w\-']*)*)"
        )
        prep_m = PREP_ORG_RE.search(after)
        if prep_m:
            obj = prep_m.group(1)
        else:
            # prefer determiner-led noun phrases like 'the company' before other nouns
            DET_RE = re.compile(
                r"\b(the|a|an)\s+([A-Za-z0-9][\w\-']*(?:\s+[A-Za-z0-9][\w\-']*)*)", re.I
            )
            det_m = DET_RE.search(after)
            if det_m:
                obj = det_m.group(0)
            else:
                obj_match = _NOUN_RE.search(after)
                obj = obj_match.group(1) if obj_match else after.strip().strip(".")

    # canonicalize phrases to lowercase and strip
    subj = subject.strip().lower()
    pred = verb.strip().lower()
    obj = obj.strip().lower()

    if not subj and not obj:
        return []

    return [(subj, pred, obj)]
