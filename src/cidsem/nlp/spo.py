import re
from typing import List, Tuple

# Very small, rule-based SPO extractor for prototyping.
# Input: sentence string
# Output: list of (subject, predicate, object) tuples as simple phrases

# match capitalized names/organizations (imperfect but useful for English)
_NOUN_RE = re.compile(r"\b([A-Z][a-zA-Z]*(?:\s+[A-Z][a-zA-Z]*)*)\b")

# Ordered verb patterns (longer/more specific first) mapped to normalized predicate
_VERB_PATTERNS = [
    (r"was hired", "hired"),
    (r"is hired", "hired"),
    (r"joined", "joined"),
    (r"was located", "located at"),
    (r"located at", "located at"),
    (r"works as", "works as"),
    (r"works", "works as"),
    (r"work", "works as"),
    (r"hired", "hired"),
    (r"left", "left"),
    (r"became", "became"),
    (r"was", "be"),
    (r"is", "be"),
    (r"are", "be"),
    (r"were", "be"),
]


def _find_nouns(text: str):
    return [(m.start(), m.group(1)) for m in _NOUN_RE.finditer(text)]


def _normalize(text: str) -> str:
    return text.strip().lower()


def extract_spo(sentence: str) -> List[Tuple[str, str, str]]:
    s = sentence.strip()
    if not s:
        return []

    # Simple sentence splitter with start offsets
    sentences = [
        (m.group(0).strip(), m.start())
        for m in re.finditer(r"[^.?!]+[.?!]?", s)
        if m.group(0).strip()
    ]

    results: List[Tuple[str, str, str]] = []

    # Collect all capitalized tokens with absolute positions for antecedent resolution
    all_nouns = [(m.start(), m.group(1)) for m in _NOUN_RE.finditer(s)]

    for sent, sent_start in sentences:
        lower = sent.lower()
        # find verbs in this sentence
        verb_spans: List[Tuple[int, int, str]] = []
        for pattern, norm in _VERB_PATTERNS:
            for m in re.finditer(re.escape(pattern), lower):
                verb_spans.append((m.start(), m.end(), norm))
        if not verb_spans:
            continue

        # find nouns in this sentence with local positions
        local_nouns = [(m.start(), m.group(1)) for m in _NOUN_RE.finditer(sent)]

        # for each verb occurrence, produce a triple
        for vstart, vend, verb in sorted(verb_spans, key=lambda x: x[0]):
            # subject heuristics:
            # - if sentence contains a pronoun (he/she/they) before the verb, resolve to
            #   the most recent single-token capitalized noun in the entire text
            # - else prefer nearest capitalized phrase before the verb in the sentence
            # only consider third-person pronouns for antecedent resolution
            pronoun_match = re.search(
                r"\b(he|she|they|it|his|her)\b", sent[:vstart], re.I
            )
            subject = ""
            if pronoun_match and all_nouns:
                # compute absolute pronoun position
                pron_rel = pronoun_match.start()
                pron_abs = sent_start + pron_rel
                # consider only nouns that occur before the pronoun
                prior_nouns = [n for (pos, n) in all_nouns if pos < pron_abs]
                if prior_nouns:
                    # choose last single-token capitalized noun in prior_nouns if available
                    singles = [
                        n for n in prior_nouns if " " not in n and not n.isupper()
                    ]
                    subject = singles[-1] if singles else prior_nouns[-1]
                else:
                    # no antecedent found; keep the pronoun as the subject
                    subject = pronoun_match.group(1)
            else:
                # nearest capitalized noun before verb in sentence
                # nearest capitalized noun before verb in sentence (local positions)
                candidates = [(pos, tok) for (pos, tok) in local_nouns if pos < vstart]
                # filter out likely interjection tokens at sentence start (e.g., "Hey, ...")
                filtered = [
                    c
                    for c in candidates
                    if not (
                        c[0] == 0 and c[1].lower() in ("hey", "hi", "hello", "once")
                    )
                ]
                use_candidates = filtered if filtered else candidates
                if use_candidates:
                    subject = sorted(use_candidates, key=lambda x: x[0])[-1][1]

            # object heuristics: immediate capitalized noun after verb, or preposition-led
            after = sent[vend:]
            obj = ""
            start_match = _NOUN_RE.match(after.lstrip())
            if start_match:
                obj = start_match.group(1)
            else:
                PREP_ORG_RE = re.compile(
                    r"\b(?:at|for|with|from|to|in|by)\s+([A-Z][A-Za-z0-9][\w\-']*(?:\s+[A-Z][A-Za-z0-9][\w\-']*)*)"
                )
                prep_m = PREP_ORG_RE.search(after)
                if prep_m:
                    obj = prep_m.group(1)
                else:
                    DET_RE = re.compile(
                        r"\b(the|a|an)\s+([A-Za-z0-9][\w\-']*(?:\s+[A-Za-z0-9][\w\-']*)*)",
                        re.I,
                    )
                    det_m = DET_RE.search(after)
                    if det_m:
                        obj = det_m.group(0)
                    else:
                        obj_match = _NOUN_RE.search(after)
                        obj = (
                            obj_match.group(1)
                            if obj_match
                            else after.strip().strip(".")
                        )

            subj_norm = _normalize(subject) if subject else ""
            pred_norm = verb.strip().lower()
            obj_norm = _normalize(obj) if obj else ""

            if not subj_norm and not obj_norm:
                continue
            results.append((subj_norm, pred_norm, obj_norm))

    # deduplicate preserving order
    seen = set()
    deduped: List[Tuple[str, str, str]] = []
    for t in results:
        if t not in seen:
            seen.add(t)
            deduped.append(t)

    # reorder triples to prefer stronger/action predicates (e.g., joined/hired)
    # so that generated factoid ids align with expectations in fixtures.
    priority = {
        "joined": 0,
        "hired": 0,
        "works as": 1,
        "works": 1,
        "left": 2,
        "became": 3,
        "be": 5,
    }

    indexed = list(enumerate(deduped))
    indexed.sort(key=lambda iv: (priority.get(iv[1][1], 10), iv[0]))
    ordered = [t for _, t in indexed]
    return ordered
