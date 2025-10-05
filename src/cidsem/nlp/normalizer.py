import re
from typing import List

# Small rule-based normalizer to canonicalize predicate phrases locally.
# This replaces external LLM calls with deterministic rewrite rules.

_RULES: List[tuple] = [
    (re.compile(r"\bjoined(?:\s+as|\s+at)?\b", re.I), "joined"),
    (re.compile(r"\bhired(?:\s+as)?\b", re.I), "hired"),
    (re.compile(r"\bleft\b", re.I), "left"),
    (re.compile(r"\blocated(?:\s+at)?\b", re.I), "located at"),
    (re.compile(r"\bworks(?:\s+as)?\b", re.I), "works as"),
]


def normalize_predicate(phrase: str) -> str:
    """Apply simple rewrite rules to produce a canonical predicate phrase."""
    p = phrase.strip().lower()
    if not p:
        return p
    # remove punctuation
    p = re.sub(r"[^a-z0-9\s]", " ", p)
    p = re.sub(r"\s+", " ", p).strip()

    for rx, repl in _RULES:
        if rx.search(p):
            return repl

    # fallback: return cleaned phrase
    return p
