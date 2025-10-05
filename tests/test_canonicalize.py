from cidsem.utils.canonicalize import canonical_cid, canonicalize_json


def test_canonical_cid_stability():
    a = {"b": 2, "a": 1}
    b = {"a": 1, "b": 2}
    assert canonicalize_json(a) == canonicalize_json(b)
    cida = canonical_cid(a)
    cidb = canonical_cid(b)
    assert cida == cidb
    assert len(cida) == 32  # 16 bytes hex
