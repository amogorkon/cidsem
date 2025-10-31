import os
import sys

# Ensure src is on sys.path for package imports during tests
ROOT = os.path.dirname(os.path.dirname(__file__))
SRC = os.path.join(ROOT, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

# Import E class for type checking
try:
    from cidsem.keys import E as EClass
except ImportError:
    EClass = None


import pytest


class InMemoryCidstore:
    """A tiny in-memory cidstore-like client for tests.

    - Supports insert(key, value), batch_insert(items), lookup(key), delete(key, value=None)
    - Keys/values may be dicts with 'high'/'low' fields, tuples, ints, or strings; they are
      normalized to tuples for internal storage.
    - batch_insert accepts a list of (key, value) tuples or a list of dicts {'key':..., 'value':...}.
    """

    def __init__(self):
        self._store = {}  # key_tuple -> set of value_tuples

    def _norm(self, x):
        # normalize common shapes to a tuple for dict-keying
        if x is None:
            return None
        if isinstance(x, tuple):
            # Expect 4-tuple for greenfield design
            if len(x) == 4:
                return x
            raise AssertionError(
                "tuple keys must be length 4 (high, high_mid, low_mid, low)"
            )
        if isinstance(x, dict):
            # Require full 4-field representation only
            if "high" in x and "high_mid" in x and "low_mid" in x and "low" in x:
                return (
                    int(x["high"]),
                    int(x["high_mid"]),
                    int(x["low_mid"]),
                    int(x["low"]),
                )
            raise AssertionError("dict keys must contain high, high_mid, low_mid, low")
            # fallback: sort items
        # If it's an E-like object with four lanes, return full 4-tuple
        if hasattr(x, "high") and hasattr(x, "low"):
            try:
                high = int(x.high)
                high_mid = int(getattr(x, "high_mid"))
                low_mid = int(getattr(x, "low_mid"))
                low = int(x.low)
                return (high, high_mid, low_mid, low)
            except (AttributeError, TypeError):
                pass

        if isinstance(x, (int, str)):
            return (str(x),)

        # fallback: represent other forms as repr
        return (repr(x),)

    def insert(self, key, value):
        k = self._norm(key)
        v = self._norm(value)
        self._store.setdefault(k, set()).add(v)
        return True

    def batch_insert(self, items):
        # items can be [(k,v), ...] or [{'key':k,'value':v}, ...]
        for it in items:
            if isinstance(it, dict):
                k = it.get("key")
                v = it.get("value")
            else:
                k, v = it
            self.insert(k, v)
        return True

    def lookup(self, key):
        k = self._norm(key)
        vals = self._store.get(k, set())
        return list(vals)

    def delete(self, key, value=None):
        k = self._norm(key)
        if k not in self._store:
            return False
        if value is None:
            del self._store[k]
            return True
        v = self._norm(value)
        if v in self._store[k]:
            self._store[k].remove(v)
            if not self._store[k]:
                del self._store[k]
            return True
        return False


@pytest.fixture
def cidstore_client():
    """Provide a fresh in-memory cidstore client for tests.

    Tests may use this fixture directly or monkeypatch application code to use it.
    """
    return InMemoryCidstore()
