"""keys.py - Entity (E) logic and key utilities

ZVIC-constrained module: enforces 256-bit CID contracts at runtime.
"""

from __future__ import annotations

import os
from uuid import NAMESPACE_DNS, uuid4, uuid5

import numpy as np
from numpy.typing import NDArray
from zvic import constrain_this_module

from .jackhash import JACK_as_num


# Import assumption function inline to avoid circular imports
def assumption(obj, *expected):
    for exp in expected:
        if isinstance(obj, exp):
            return True
    raise AssertionError(f"Expected {expected}, got {type(obj).__name__}")


_kv_store: dict[int, str] = {}

# Enable ZVIC runtime constraint checking if not explicitly disabled.
# Use environment variable `CIDSEM_ZVIC_ENABLED` (default: "1").
try:
    if os.getenv("CIDSEM_ZVIC_ENABLED", "1") == "1":
        constrain_this_module()
except Exception:
    # Be conservative on import errors: don't block import if ZVIC is misconfigured.
    pass

# 256-bit E: four 64-bit parts
KEY_DTYPE = np.dtype([
    ("high", "<u8"),
    ("high_mid", "<u8"),
    ("low_mid", "<u8"),
    ("low", "<u8"),
])

HASH_ENTRY_DTYPE = np.dtype([
    ("key_high", "<u8"),
    ("key_high_mid", "<u8"),
    ("key_low_mid", "<u8"),
    ("key_low", "<u8"),
    (
        "slots",
        [("high", "<u8"), ("high_mid", "<u8"), ("low_mid", "<u8"), ("low", "<u8")],
        2,
    ),
    ("checksum", "<u8", 4),  # 4 x uint64 for checksum (u256)
])


class E(int):
    """
    E: 256-bit entity identifier for CIDStore keys/values.

    - Immutable, hashable, and convertible to/from HDF5.
    - Represented as four 64-bit unsigned parts: high, high_mid, low_mid, low.
    - Backwards compatible: accepts 2-part (128-bit) tuples which are zero-extended into the lower 128 bits.
    """

    def __getitem__(self, item):
        assert item in ("high", "high_mid", "low_mid", "low"), (
            "item must be one of the 4 parts"
        )
        return [getattr(self, item)]

    __slots__ = ()

    def __new__(
        cls,
        id_: "int[_ >= 0 and _ < (1 << 256)] | str | list[int][len(_) == 4] | tuple[int, ...][len(_) == 4] | None" = None,
    ) -> E:
        # Delegate to from_jackhash if a string is passed that looks like a JACK hash
        if isinstance(id_, str):
            return cls.from_jackhash(id_)
        if isinstance(id_, (list, tuple, np.void)):
            # Require 4-part tuple/list for E in the greenfield design
            if len(id_) == 4:
                for i in id_:
                    assert assumption(i, int, np.uint64)
                a, b_, c, d = id_
                return cls.from_int(
                    (int(a) << 192) | (int(b_) << 128) | (int(c) << 64) | int(d)
                )
            else:
                raise AssertionError("input list/tuple must be length 4 for E")
        if id_ is None:
            id_ = uuid4().int
        return super().__new__(cls, id_)

    @property
    def value(self) -> str | None:
        return _kv_store.get(self)

    @property
    def high(self) -> "int[_ >= 0 and _ < (1 << 64)]":
        return (self >> 192) & ((1 << 64) - 1)

    @property
    def high_mid(self) -> "int[_ >= 0 and _ < (1 << 64)]":
        return (self >> 128) & ((1 << 64) - 1)

    @property
    def low_mid(self) -> "int[_ >= 0 and _ < (1 << 64)]":
        return (self >> 64) & ((1 << 64) - 1)

    @property
    def low(self) -> "int[_ >= 0 and _ < (1 << 64)]":
        return self & ((1 << 64) - 1)

    def __repr__(self) -> str:
        # Represent as E(h,hm,lm,l)
        return f"E({self.high},{self.high_mid},{self.low_mid},{self.low})"

    def __str__(self) -> str:
        return self.__repr__()

    def to_hdf5(self) -> NDArray[np.void]:
        """Convert to HDF5-compatible array"""
        return np.array(
            (self.high, self.high_mid, self.low_mid, self.low), dtype=KEY_DTYPE
        )

    @classmethod
    def from_entry(cls, entry: NDArray[np.void]) -> E:
        """
        Create an E from an HDF5 row. Accepts fields for 4-part entries or legacy 2-part.
        """
        fields = entry.dtype.fields
        if fields is not None:
            # Expect 4-part structured array only
            if (
                "high" in fields
                and "high_mid" in fields
                and "low_mid" in fields
                and "low" in fields
            ):
                a = int(entry["high"])
                b_ = int(entry["high_mid"])
                c = int(entry["low_mid"])
                d = int(entry["low"])
                return cls.from_int((a << 192) | (b_ << 128) | (c << 64) | d)
            else:
                raise ValueError(
                    "Input must have 'high','high_mid','low_mid','low' fields for E"
                )
        raise ValueError(
            "Input must have appropriate high/high_mid/low_mid/low or legacy fields"
        )

    @classmethod
    def from_int(cls, id_: "int[_ >= 0 and _ < (1 << 256)]") -> E:
        """
        Create an E from an integer.
        """
        assert assumption(id_, int)
        assert id_ is not None and 0 <= id_ < (1 << 256), "ID must be a 256-bit integer"
        return cls(id_)

    @classmethod
    def from_jackhash(cls, value: str) -> E:
        """
        Create an E from a JACK hash string.
        JACK_as_num should produce an integer that fits within 256 bits for our use.
        """
        return cls(JACK_as_num(value))

    @classmethod
    def from_str(cls, value: str) -> E:
        assert assumption(value, str)
        # Use SHA-based deterministic namespace via uuid5 for backward compatibility in some places
        id_ = uuid5(NAMESPACE_DNS, value).int
        _kv_store.setdefault(id_, value)
        return cls(id_)

    @classmethod
    def from_hdf5(cls, arr: NDArray[np.void]) -> E:
        """
        Create an E from an HDF5-compatible array (as produced by to_hdf5).
        Accepts a numpy structured array with 4 fields.
        """
        assert hasattr(arr, "dtype"), "Input must have a dtype attribute (numpy array)"
        assert arr.dtype == HASH_ENTRY_DTYPE
        assert arr.dtype.fields is not None
        assert (
            "high" in arr.dtype.fields
            and "high_mid" in arr.dtype.fields
            and "low_mid" in arr.dtype.fields
            and "low" in arr.dtype.fields
        ), "Structured array must have 'high','high_mid','low_mid','low' fields"
        a = int(arr["high"])
        b_ = int(arr["high_mid"])
        c = int(arr["low_mid"])
        d = int(arr["low"])
        return cls.from_int((a << 192) | (b_ << 128) | (c << 64) | d)
