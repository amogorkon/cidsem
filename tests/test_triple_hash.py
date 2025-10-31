"""Tests for triple hashing and cache integration."""

from cidsem.cidstore import TripleRecord
from cidsem.hashcache import get_triple_hash
from cidsem.keys import E


def test_triple_hash_consistency():
    s = E.from_str("Alice")
    p = E.from_str("worksAt")
    o = E.from_str("BetaCorp")
    t = TripleRecord(s, p, o)

    h1, e1 = get_triple_hash(t)
    h2, e2 = get_triple_hash(t)

    assert isinstance(h1, str) and len(h1) == 64
    assert h1 == h2
    assert isinstance(e1, E)
    assert e1 == e2


def test_provenance_contains_hash():
    s = E.from_str("Alice")
    p = E.from_str("worksAt")
    o = E.from_str("BetaCorp")
    t = TripleRecord(s, p, o)
    # simulate what extract_context_to_triples does: compute hash
    h, e = get_triple_hash(t)
    t.provenance["triple_hash"] = h
    t.provenance["triple_hash_e"] = e

    assert "triple_hash" in t.provenance
    assert "triple_hash_e" in t.provenance
    assert t.provenance["triple_hash"] == h
    assert t.provenance["triple_hash_e"] == e
