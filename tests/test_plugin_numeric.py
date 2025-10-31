"""
Tests for NumericRangeDS plugin.
"""

import pytest

from cidsem.plugins.base import QueryCapability
from cidsem.plugins.numeric import NumericRangeDS


class TestNumericRangeDS:
    """Test numeric range plugin functionality."""

    @pytest.mark.asyncio
    async def test_basic_numeric_storage(self):
        """Test basic get/set with numeric values."""
        plugin = NumericRangeDS()
        plugin.configure({})

        await plugin.set("alice", 5)
        await plugin.set("bob", 10)
        await plugin.set("charlie", 3)

        assert await plugin.get("alice") == 5
        assert await plugin.get("bob") == 10
        assert await plugin.get("charlie") == 3

    @pytest.mark.asyncio
    async def test_numeric_bounds_validation(self):
        """Test min/max value enforcement."""
        plugin = NumericRangeDS()
        plugin.configure({
            "min_value": 0,
            "max_value": 100,
        })

        # Valid values
        await plugin.set("alice", 50)
        assert await plugin.get("alice") == 50

        # Below minimum
        with pytest.raises(ValueError, match="below minimum"):
            await plugin.set("bob", -1)

        # Above maximum
        with pytest.raises(ValueError, match="above maximum"):
            await plugin.set("charlie", 101)

    @pytest.mark.asyncio
    async def test_type_validation(self):
        """Test that non-numeric values are rejected."""
        plugin = NumericRangeDS()
        plugin.configure({})

        with pytest.raises(TypeError, match="requires numeric value"):
            await plugin.set("alice", "not a number")

    @pytest.mark.asyncio
    async def test_reverse_lookup(self):
        """Test POS queries via find_subjects()."""
        plugin = NumericRangeDS()
        plugin.configure({})

        await plugin.set("alice", 5)
        await plugin.set("bob", 5)
        await plugin.set("charlie", 10)

        # Find all subjects with value 5
        subjects = await plugin.find_subjects(5)
        assert set(subjects) == {"alice", "bob"}

        # Find subjects with value 10
        subjects = await plugin.find_subjects(10)
        assert subjects == ["charlie"]

        # Non-existent value
        subjects = await plugin.find_subjects(99)
        assert subjects == []

    @pytest.mark.asyncio
    async def test_range_queries(self):
        """Test range queries with find_subjects_in_range()."""
        plugin = NumericRangeDS()
        plugin.configure({})

        await plugin.set("alice", 5)
        await plugin.set("bob", 10)
        await plugin.set("charlie", 15)
        await plugin.set("david", 20)

        # Range [5, 15]
        subjects = await plugin.find_subjects_in_range(5, 15)
        assert set(subjects) == {"alice", "bob", "charlie"}

        # Range [10, 20]
        subjects = await plugin.find_subjects_in_range(10, 20)
        assert set(subjects) == {"bob", "charlie", "david"}

        # Range [100, 200] (empty)
        subjects = await plugin.find_subjects_in_range(100, 200)
        assert subjects == []

    @pytest.mark.asyncio
    async def test_update_maintains_indices(self):
        """Test that updates correctly maintain both indices."""
        plugin = NumericRangeDS()
        plugin.configure({})

        # Initial set
        await plugin.set("alice", 5)
        assert await plugin.get("alice") == 5
        assert set(await plugin.find_subjects(5)) == {"alice"}

        # Update to new value
        await plugin.set("alice", 10)
        assert await plugin.get("alice") == 10

        # Old value should have no subjects
        assert await plugin.find_subjects(5) == []

        # New value should have alice
        assert set(await plugin.find_subjects(10)) == {"alice"}

    @pytest.mark.asyncio
    async def test_delete_maintains_indices(self):
        """Test that delete removes from both indices."""
        plugin = NumericRangeDS()
        plugin.configure({})

        await plugin.set("alice", 5)
        await plugin.set("bob", 5)

        # Both in range index
        assert set(await plugin.find_subjects(5)) == {"alice", "bob"}

        # Delete alice
        assert await plugin.delete("alice") is True

        # Only bob remains
        assert await plugin.find_subjects(5) == ["bob"]
        assert await plugin.get("alice") is None

    @pytest.mark.asyncio
    async def test_capabilities(self):
        """Test that NumericRangeDS declares correct capabilities."""
        plugin = NumericRangeDS()
        capabilities = plugin.supported_capabilities()

        assert QueryCapability.SPO in capabilities
        assert QueryCapability.OSP in capabilities
        assert QueryCapability.POS in capabilities
        assert QueryCapability.RANGE in capabilities

    @pytest.mark.asyncio
    async def test_health_check_metrics(self):
        """Test health check includes useful metrics."""
        plugin = NumericRangeDS()
        plugin.configure({})

        await plugin.set("alice", 5)
        await plugin.set("bob", 5)
        await plugin.set("charlie", 10)

        health = await plugin.health_check()

        assert health["status"] == "ok"
        assert health["metrics"]["subject_count"] == 3
        assert health["metrics"]["unique_values"] == 2
        assert health["metrics"]["avg_subjects_per_value"] == 1.5

    @pytest.mark.asyncio
    async def test_snapshot_and_restore(self):
        """Test snapshot preserves range indices."""
        plugin1 = NumericRangeDS()
        plugin1.configure({"min_value": 0, "max_value": 100})

        await plugin1.set("alice", 5)
        await plugin1.set("bob", 10)
        await plugin1.set("charlie", 5)

        # Snapshot
        snapshot = await plugin1.snapshot()

        # Restore
        plugin2 = NumericRangeDS()
        await plugin2.restore_snapshot(snapshot)

        # Verify primary index
        assert await plugin2.get("alice") == 5
        assert await plugin2.get("bob") == 10

        # Verify reverse index
        assert set(await plugin2.find_subjects(5)) == {"alice", "charlie"}
        assert await plugin2.find_subjects(10) == ["bob"]

        # Verify config
        assert plugin2.config == {"min_value": 0, "max_value": 100}
