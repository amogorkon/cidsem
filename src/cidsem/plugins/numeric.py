"""
Numeric range plugin with bidirectional indices.

Optimized for numeric predicates that need efficient reverse lookups and
range queries (e.g., hasApple, hasAge, hasPrice).
"""

import asyncio
from typing import Any, List, Optional

from sortedcontainers import SortedDict

from .base import DataStructurePlugin, QueryCapability


class NumericRangeDS(DataStructurePlugin):
    """
    Plugin for numeric predicates with range query support.

    Maintains two indices:
    1. subject -> value (primary, for SPO queries)
    2. value -> set(subjects) (reverse, for POS and range queries)

    Suitable for: counts, quantities, ages, prices, ratings, etc.
    """

    def __init__(self):
        super().__init__()
        self.data = {}  # subject -> value
        self.range_index = SortedDict()  # value -> set(subjects)
        self._update_lock = asyncio.Lock()  # Prevent race conditions on updates

    def configure(self, config: dict):
        super().configure(config)

        # Validate numeric bounds if provided
        self.min_value = config.get("min_value")
        self.max_value = config.get("max_value")
        self.default_value = config.get("default_value", 0)

        if self.min_value is not None and self.max_value is not None:
            if self.min_value >= self.max_value:
                raise ValueError(
                    f"min_value ({self.min_value}) must be < max_value ({self.max_value})"
                )

    def supported_capabilities(self) -> List[QueryCapability]:
        return [
            QueryCapability.SPO,
            QueryCapability.OSP,
            QueryCapability.POS,
            QueryCapability.RANGE,
        ]

    async def get(self, subject: str) -> Optional[int]:
        return self.data.get(subject)

    async def set(self, subject: str, object_value: Any):
        # Validate numeric value
        if not isinstance(object_value, (int, float)):
            raise TypeError(
                f"NumericRangeDS requires numeric value, got {type(object_value)}"
            )

        # Validate bounds
        if self.min_value is not None and object_value < self.min_value:
            raise ValueError(f"Value {object_value} below minimum {self.min_value}")
        if self.max_value is not None and object_value > self.max_value:
            raise ValueError(f"Value {object_value} above maximum {self.max_value}")

        async with self._update_lock:
            # Remove old value from reverse index
            old_value = self.data.get(subject)
            if old_value is not None and old_value in self.range_index:
                self.range_index[old_value].discard(subject)
                if not self.range_index[old_value]:
                    del self.range_index[old_value]

            # Add new value to both indices
            self.data[subject] = object_value

            if object_value not in self.range_index:
                self.range_index[object_value] = set()
            self.range_index[object_value].add(subject)

    async def delete(self, subject: str) -> bool:
        async with self._update_lock:
            old_value = self.data.get(subject)
            if old_value is None:
                return False

            # Remove from both indices
            del self.data[subject]

            if old_value in self.range_index:
                self.range_index[old_value].discard(subject)
                if not self.range_index[old_value]:
                    del self.range_index[old_value]

            return True

    async def contains(self, subject: str, object_value: Any) -> bool:
        # Optimized OSP: direct dictionary lookup (O(1))
        return self.data.get(subject) == object_value

    async def find_subjects(self, object_value: Any) -> List[str]:
        # Optimized POS: use range index (O(1) for exact match)
        subjects = self.range_index.get(object_value, set())
        return list(subjects)

    async def find_subjects_in_range(self, min_val: float, max_val: float) -> List[str]:
        """
        Range query: Find all subjects with values in [min_val, max_val].

        Uses SortedDict for efficient range iteration.
        """
        if min_val > max_val:
            raise ValueError(f"min_val ({min_val}) must be <= max_val ({max_val})")

        results = []

        # SortedDict.irange() efficiently iterates values in range
        for value in self.range_index.irange(min_val, max_val):
            results.extend(self.range_index[value])

        return results

    async def health_check(self) -> dict:
        base = await super().health_check()
        base["metrics"] = {
            "subject_count": len(self.data),
            "unique_values": len(self.range_index),
            "avg_subjects_per_value": (
                len(self.data) / len(self.range_index) if self.range_index else 0
            ),
        }
        return base

    async def snapshot(self) -> dict:
        base = await super().snapshot()
        base["data"] = {
            "subjects": dict(self.data),
            # Serialize range_index (SortedDict -> dict, sets -> lists)
            "range_index": {
                str(value): list(subjects)
                for value, subjects in self.range_index.items()
            },
        }
        return base

    async def restore_snapshot(self, snapshot: dict):
        await super().restore_snapshot(snapshot)

        data = snapshot.get("data", {})
        self.data = dict(data.get("subjects", {}))

        # Restore range_index
        self.range_index = SortedDict()
        for value_str, subjects_list in data.get("range_index", {}).items():
            value = float(value_str)
            self.range_index[value] = set(subjects_list)
