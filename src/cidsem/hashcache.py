"""hashcache.py - compute and cache triple SHA-256 hashes and E conversion

Provides utilities to compute a deterministic SHA-256 over the canonical
binary serialization of a triple (subject,predicate,object) where each E
is represented as four 64-bit unsigned integers in big-endian order.

The SHA-256 digest is returned both as a hex string and as an `E` value
constructed from the 256-bit digest. An LRU cache is used to avoid
recomputing hashes for repeated triples.
"""

from __future__ import annotations

import hashlib
import struct
from functools import lru_cache
from typing import Tuple

from .keys import E


def _tuple_from_triple(triple) -> Tuple[int, ...]:
    """Return a flat tuple of 12 integers representing S,P,O (4 lanes each)."""
    s = triple.subject
    p = triple.predicate
    o = triple.object
    return (
        int(s.high),
        int(s.high_mid),
        int(s.low_mid),
        int(s.low),
        int(p.high),
        int(p.high_mid),
        int(p.low_mid),
        int(p.low),
        int(o.high),
        int(o.high_mid),
        int(o.low_mid),
        int(o.low),
    )


@lru_cache(maxsize=16384)
def compute_hash_from_tuple(key: Tuple[int, ...]) -> Tuple[str, E]:
    """Compute SHA-256 hex digest and E from a tuple of ints.

    key: tuple of 12 ints (s.h, s.hm, s.lm, s.l, p.h, ... , o.l)
    returns (hex_digest, E_from_digest)
    """
    # Pack as big-endian unsigned 64-bit words
    b = b"".join(struct.pack(">Q", int(x) & ((1 << 64) - 1)) for x in key)
    h = hashlib.sha256(b).digest()
    hexdig = h.hex()
    # Convert digest (big-endian) to integer then to E
    intval = int.from_bytes(h, "big")
    e = E.from_int(intval)
    return (hexdig, e)


def get_triple_hash(triple) -> Tuple[str, E]:
    """Return cached (hex_digest, E) for the given TripleRecord.

    Uses an LRU cache keyed by the numeric components of the triple.
    """
    key = _tuple_from_triple(triple)
    return compute_hash_from_tuple(key)
