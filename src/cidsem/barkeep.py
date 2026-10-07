"""
barkeep.py — memory adapter for the Barkeep AI persona.

This is the CID-aware side of the Barkeep memory round-trip.
Callers (Barkeep in plex-com) pass plain Python values; this module
translates them into E-keyed triples and stores/retrieves them.

Separation of concerns
-----------------------
Barkeep knows:  persona_id (int), topic keyword (str), message text.
This module knows: E types, compound keys, the triple shape.
Cidstore knows: nothing about either.

POC backend: in-process dict.  Swap ``_backend`` for a CidstoreClient
instance to get real persistence with no changes to callers.

Usage (from plex-com, no CID knowledge required)::

    from cidsem.barkeep import remember, recall

    remember(42, "karma", "what is karma?", "Karma is ...")
    topics = recall(42)   # → ["karma"]
"""

from __future__ import annotations

from .keys import E

# ---------------------------------------------------------------------------
# Stable predicate CIDs — deterministic via from_str
# ---------------------------------------------------------------------------

_ASKED_ABOUT: E = E.from_str("barkeep:predicate:asked_about")

# ---------------------------------------------------------------------------
# POC backend: in-process dict
# compound_key_int → list of topic E ints (deduplicated)
# Swap this for a CidstoreClient to get real persistence.
# ---------------------------------------------------------------------------

_store: dict[int, list[int]] = {}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _persona_cid(persona_id: int) -> E:
    return E.from_str(f"tavern:persona:{persona_id}")


def _topic_cid(topic: str) -> E:
    # Normalise to lower-case so "Karma" and "karma" map to the same CID.
    # E.from_str also stores the value in _kv_store for free reverse lookup.
    return E.from_str(f"tavern:topic:{topic.lower()}")


def _compound_key(subject: E, predicate: E) -> int:
    """XOR the low 64-bit lanes — mirrors CidstoreClient.create_compound_key."""
    return (int(subject) ^ int(predicate)) & ((1 << 256) - 1)


# ---------------------------------------------------------------------------
# Public API (domain-level; no CID types exposed to callers)
# ---------------------------------------------------------------------------

def remember(
    persona_id: int,
    topic: str,
    question: str,  # noqa: ARG001 — reserved for future content CID
    response: str,  # noqa: ARG001 — reserved for future content CID
) -> None:
    """Record that *persona_id* asked about *topic*.

    Args:
        persona_id: Tavern persona integer ID.
        topic:      Normalised keyword extracted by Barkeep ("karma", "veil", …).
        question:   Raw question text (reserved for future content-CID storage).
        response:   Barkeep's response text (reserved for future content-CID storage).
    """
    s = _persona_cid(persona_id)
    t = _topic_cid(topic)
    key = _compound_key(s, _ASKED_ABOUT)
    bucket = _store.setdefault(key, [])
    t_int = int(t)
    if t_int not in bucket:
        bucket.append(t_int)


def recall(persona_id: int) -> list[str]:
    """Return the topic keywords previously stored for *persona_id*.

    Returns an empty list if nothing has been stored yet.

    The reverse lookup is free: ``E.from_str`` registers every string in
    ``_kv_store``, so ``E.value`` resolves back to the original string.
    We strip the ``"tavern:topic:"`` namespace prefix before returning.
    """
    s = _persona_cid(persona_id)
    key = _compound_key(s, _ASKED_ABOUT)
    topics: list[str] = []
    for t_int in _store.get(key, []):
        e = E.from_int(t_int)
        raw = e.value  # e.g. "tavern:topic:karma"
        if raw and raw.startswith("tavern:topic:"):
            topics.append(raw[len("tavern:topic:"):])
    return topics
