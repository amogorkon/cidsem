"""
Base plugin interface for predicate-specific data structures.

Plugins provide specialized storage and query optimizations for specific
predicates while maintaining compatibility with cidstore's primary compound
key storage.
"""

import asyncio
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, List


class QueryCapability(Enum):
    """Query patterns supported by a plugin."""

    SPO = "spo"  # Subject-Predicate-Object (primary, always via cidstore)
    OSP = "osp"  # Object-Subject-Predicate (reverse lookup)
    POS = "pos"  # Predicate-Object-Subject (object enumeration)
    RANGE = "range"  # Range queries (numeric, temporal)
    SPATIAL = "spatial"  # Spatial queries (geo, proximity)
    FULLTEXT = "fulltext"  # Full-text search


class DataStructurePlugin(ABC):
    """
    Base class for predicate-specific data structure plugins.

    Plugins augment cidstore's primary compound key storage with specialized
    indices for efficient reverse lookups and domain-specific queries.

    All plugins must implement get() and set(). Optional capabilities (OSP, POS,
    etc.) can be implemented by overriding the corresponding methods and declaring
    support via supported_capabilities().
    """

    def __init__(self):
        self.config = {}
        self._lock = asyncio.Lock()  # For thread-safe operations

    def configure(self, config: dict):
        """
        Configure the plugin with predicate-specific settings.

        Called once during plugin initialization. Configuration should be
        validated here and stored for later use.
        """
        self.config = config

    def supported_capabilities(self) -> List[QueryCapability]:
        """
        Declare which query patterns this plugin supports.

        Default: Only SPO (via cidstore primary storage).
        Override to declare OSP, POS, or other specialized capabilities.
        """
        return [QueryCapability.SPO]

    @abstractmethod
    async def get(self, subject: str) -> Any:
        """
        SPO: Get object value for subject (predicate is implicit).

        This is the primary query method. Must be implemented by all plugins.
        Returns None if subject doesn't exist.
        """
        pass

    @abstractmethod
    async def set(self, subject: str, object_value: Any):
        """
        Store subject-object pair (predicate is implicit).

        This is the primary storage method. Must be implemented by all plugins.
        Should be idempotent: setting the same value twice has no additional effect.
        """
        pass

    async def delete(self, subject: str) -> bool:
        """
        Remove subject-object pair.

        Returns True if subject existed and was removed, False otherwise.
        Optional: plugins can override for efficient deletion.
        """
        # Default implementation: check existence then remove
        value = await self.get(subject)
        if value is None:
            return False

        # Derived classes should override this with actual deletion logic
        raise NotImplementedError("Plugin must implement delete()")

    async def contains(self, subject: str, object_value: Any) -> bool:
        """
        OSP optimization: Check if subject has object_value.

        Default implementation uses get() and compares. Plugins can override
        for more efficient membership testing (e.g., bloom filters, hash sets).
        """
        current_value = await self.get(subject)
        return current_value == object_value

    async def find_subjects(self, object_value: Any) -> List[str]:
        """
        POS: Find all subjects with object_value (reverse lookup).

        Default raises NotImplementedError. Plugins that support reverse
        lookups should override this and declare QueryCapability.POS in
        supported_capabilities().
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} does not support POS queries (find_subjects)"
        )

    async def health_check(self) -> dict:
        """
        Check plugin health and return status.

        Returns dict with 'status' (ok/degraded/error), 'message', and optional
        'metrics' (latency, error_rate, memory_usage, etc.).
        """
        return {
            "status": "ok",
            "plugin": self.__class__.__name__,
            "config": self.config,
        }

    async def snapshot(self) -> dict:
        """
        Create a serializable snapshot of plugin state.

        Used for persistence and recovery. Should return a JSON-serializable dict
        that can be restored via restore_snapshot().
        """
        return {
            "plugin_class": self.__class__.__name__,
            "config": self.config,
            "data": {},  # Derived classes should include actual data
        }

    async def restore_snapshot(self, snapshot: dict):
        """
        Restore plugin state from a snapshot.

        Called during recovery. Should validate snapshot and restore internal state.
        """
        if snapshot.get("plugin_class") != self.__class__.__name__:
            raise ValueError(
                f"Snapshot is for {snapshot.get('plugin_class')}, "
                f"not {self.__class__.__name__}"
            )

        self.config = snapshot.get("config", {})
        # Derived classes should restore actual data


class DefaultDataStructure(DataStructurePlugin):
    """
    Default in-memory plugin for predicates without specialized requirements.

    Simple dict-based storage. Suitable for small to medium predicates where
    specialized indices aren't needed.
    """

    def __init__(self):
        super().__init__()
        self.data = {}  # subject -> object

    async def get(self, subject: str) -> Any:
        return self.data.get(subject)

    async def set(self, subject: str, object_value: Any):
        async with self._lock:
            self.data[subject] = object_value

    async def delete(self, subject: str) -> bool:
        async with self._lock:
            if subject in self.data:
                del self.data[subject]
                return True
            return False

    async def snapshot(self) -> dict:
        base = await super().snapshot()
        base["data"] = dict(self.data)
        return base

    async def restore_snapshot(self, snapshot: dict):
        await super().restore_snapshot(snapshot)
        self.data = dict(snapshot.get("data", {}))
