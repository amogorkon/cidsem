import json
import os
from difflib import SequenceMatcher
from typing import Optional

from cidsem.nlp.normalizer import normalize_predicate

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
SCHEMA_DIR = os.environ.get("CIDSEM_SCHEMA_DIR", os.path.join(ROOT, "docs", "spec"))
ONTO_FILE = os.path.join(SCHEMA_DIR, "ontology.json")


def load_ontology():
    try:
        return json.load(open(ONTO_FILE))
    except FileNotFoundError:
        return {"predicates": []}


def _score(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()


def map_predicate(phrase: str, threshold: float = 0.6) -> Optional[dict]:
    """Map a predicate phrase to the best ontology predicate if above threshold.
    Returns the matching predicate dict or None.
    """
    ont = load_ontology()
    best = None
    best_score = 0.0
    # normalize phrase locally before matching
    norm = normalize_predicate(phrase)
    for p in ont.get("predicates", []):
        sc = _score(norm.lower(), p.get("label", "").lower())
        if sc > best_score:
            best_score = sc
            best = p
    if best_score >= threshold:
        return {"predicate": best, "score": best_score}
    return None
