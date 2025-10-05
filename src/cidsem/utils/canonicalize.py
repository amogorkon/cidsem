import json
from hashlib import blake2b


def canonicalize_json(obj) -> str:
    """Canonicalize JSON following a simplified deterministic ordering (keys sorted)."""
    return json.dumps(obj, separators=(",", ":"), sort_keys=True, ensure_ascii=False)


def cid_from_canonical(json_str: str) -> str:
    # Use blake2b 16-byte digest (128-bit) encoded as hex
    h = blake2b(digest_size=16)
    h.update(json_str.encode("utf-8"))
    return h.hexdigest()


def canonical_cid(obj) -> str:
    s = canonicalize_json(obj)
    return cid_from_canonical(s)
