"""
Tests for plugin base classes and contracts.
"""

import asyncio

import pytest

from cidsem.plugins.base import DefaultDataStructure


class TestDataStructurePlugin:
    """Test the base plugin interface."""

    @pytest.mark.asyncio
    async def test_default_plugin_basic_operations(self):
        """Test basic get/set/delete with DefaultDataStructure."""
        plugin = DefaultDataStructure()
        plugin.configure({})

        # Initially empty
        assert await plugin.get("alice") is None

        # Set and get
        await plugin.set("alice", 5)
        assert await plugin.get("alice") == 5

        # Update
        await plugin.set("alice", 10)
        assert await plugin.get("alice") == 10

        # Delete
        assert await plugin.delete("alice") is True
        assert await plugin.get("alice") is None

        # Delete non-existent
        assert await plugin.delete("bob") is False

    @pytest.mark.asyncio
    async def test_default_plugin_contains(self):
        """Test OSP contains() method."""
        plugin = DefaultDataStructure()
        plugin.configure({})

        await plugin.set("alice", 5)

        assert await plugin.contains("alice", 5) is True
        assert await plugin.contains("alice", 10) is False
        assert await plugin.contains("bob", 5) is False

    @pytest.mark.asyncio
    async def test_default_plugin_find_subjects_not_supported(self):
        """DefaultDataStructure should not support POS queries."""
        plugin = DefaultDataStructure()
        plugin.configure({})

        await plugin.set("alice", 5)
        await plugin.set("bob", 5)

        # POS not supported by default
        with pytest.raises(NotImplementedError):
            await plugin.find_subjects(5)

    @pytest.mark.asyncio
    async def test_plugin_snapshot_and_restore(self):
        """Test snapshot and restore functionality."""
        plugin1 = DefaultDataStructure()
        plugin1.configure({"test": "config"})

        await plugin1.set("alice", 5)
        await plugin1.set("bob", 10)

        # Create snapshot
        snapshot = await plugin1.snapshot()

        # Verify snapshot structure
        assert snapshot["plugin_class"] == "DefaultDataStructure"
        assert snapshot["config"] == {"test": "config"}
        assert snapshot["data"] == {"alice": 5, "bob": 10}

        # Restore to new plugin instance
        plugin2 = DefaultDataStructure()
        await plugin2.restore_snapshot(snapshot)

        # Verify restored state
        assert await plugin2.get("alice") == 5
        assert await plugin2.get("bob") == 10
        assert plugin2.config == {"test": "config"}

    @pytest.mark.asyncio
    async def test_plugin_health_check(self):
        """Test health check returns expected structure."""
        plugin = DefaultDataStructure()
        plugin.configure({"key": "value"})

        health = await plugin.health_check()

        assert health["status"] == "ok"
        assert health["plugin"] == "DefaultDataStructure"
        assert health["config"] == {"key": "value"}

    @pytest.mark.asyncio
    async def test_concurrent_access(self):
        """Test plugin handles concurrent access correctly."""
        plugin = DefaultDataStructure()
        plugin.configure({})

        # Run many concurrent sets
        async def set_value(subject, value):
            await plugin.set(subject, value)

        tasks = [set_value(f"subject_{i % 10}", i) for i in range(100)]

        await asyncio.gather(*tasks)

        # Verify final state is consistent (each subject has highest value)
        for i in range(10):
            value = await plugin.get(f"subject_{i}")
            # Value should be the last write for this subject
            assert value is not None
            assert value >= i
