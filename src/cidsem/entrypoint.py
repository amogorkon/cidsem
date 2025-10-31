"""entrypoint.py - single entry point for cidsem pipeline

Provides a simple `process_text` function that accepts an arbitrary
string and returns a set of add-style messages representing extracted
triples. Designed for local development and tests; does not perform any
networking. Messages are returned in two forms:

- human: list of strings like "add(E(h,hm,lm,l), E(...), E(...))"
- data: a msgpack/JSON-serializable dict suitable for CIDStore compat
  `batch_insert` requests: {"command":"batch_insert","triples":[...]}.

This function uses the existing SPO extractor and ontology mapper to
produce candidate predicates. It returns an empty list if no triples
are found.
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

from .cidstore import extract_context_to_triples
from .keys import E
from .nlp.mapper import map_predicate, map_predicate_candidates
from .nlp.spo import extract_spo


def _e_to_str(e: E) -> str:
    """Return canonical string representation for an E: E(h,hm,lm,l)"""
    return f"E({e.high},{e.high_mid},{e.low_mid},{e.low})"


def _triple_to_msg(triple) -> Dict[str, Any]:
    """Convert a TripleRecord into a dict with s/p/o as E strings."""
    return {
        "s": _e_to_str(triple.subject),
        "p": _e_to_str(triple.predicate),
        "o": _e_to_str(triple.object),
    }


def process_text(
    text: str, factoid_id: str | None = None, use_llm: bool = False
) -> Tuple[List[str], Dict[str, Any]]:
    """Process an arbitrary text into cidsem add-style messages.

    Args:
        text: input text to analyze
        factoid_id: optional id used for provenance when constructing triples
        use_llm: whether to allow the mapper to use the local LLM chooser

    Returns:
        A tuple (human_msgs, batch_request) where `human_msgs` is a list of
        strings like "add(E(...), E(...), E(...))" and `batch_request` is
        a dict matching the CIDStore compat `batch_insert` request format.
    """
    # Extract SPO phrases
    spo = extract_spo(text)
    if not spo:
        return ([], {"command": "batch_insert", "triples": []})

    predicate_candidates = []
    # Map predicates and build candidates. Use the multi-candidate mapper
    # if available; fall back to the single-item mapper for compatibility.
    for subj_phrase, pred_phrase, obj_phrase in spo:
        try:
            candidates = map_predicate_candidates(
                pred_phrase,
                subject=subj_phrase,
                object=obj_phrase,
                context=text,
                top_k=3,
                use_llm=use_llm,
            )
        except Exception:
            # Fall back to single mapping for robustness
            mapped = map_predicate(pred_phrase, use_llm=use_llm)
            candidates = []
            if mapped:
                candidates.append({
                    "pred_id": mapped["predicate"].get("cid")
                    if isinstance(mapped.get("predicate"), dict)
                    else str(mapped.get("predicate")),
                    "score": mapped.get("score", 1.0),
                    "label": mapped["predicate"].get("label", "")
                    if isinstance(mapped.get("predicate"), dict)
                    else "",
                    "explanation": "fallback",
                    "backend": "rules",
                })

        # Normalize candidate entries into the expected predicate_candidates
        for idx, cand in enumerate(candidates):
            pcid = cand.get("pred_id") or cand.get("predicate_cid") or ""
            score = cand.get("score", 1.0)
            label = cand.get("label", "")
            predicate_candidates.append({
                "predicate_cid": pcid,
                "score": score,
                "label": label,
                "candidate_index": idx,
            })

    # Convert to triples using existing helper (which produces TripleRecord with E entities)
    triples = extract_context_to_triples(
        text, factoid_id or "generated", predicate_candidates
    )

    # Build human-readable messages and batch request format
    human_msgs: List[str] = []
    triples_list = []
    for t in triples:
        human_msgs.append(
            f"add({_e_to_str(t.subject)},{_e_to_str(t.predicate)},{_e_to_str(t.object)})"
        )
        triples_list.append(_triple_to_msg(t))

    batch_request = {"command": "batch_insert", "triples": triples_list}
    return (human_msgs, batch_request)


__all__ = ["process_text"]
