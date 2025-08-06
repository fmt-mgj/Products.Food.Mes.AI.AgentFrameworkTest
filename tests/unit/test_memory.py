"""Comprehensive unit tests for memory storage system."""

import asyncio
import json
import pytest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import AsyncMock, patch

from generated.memory import MemoryManager


@pytest.fixture
def temp_memory_dir():
    """Create a temporary directory for memory tests."""
    with TemporaryDirectory() as tmp_dir:
        yield tmp_dir


@pytest.fixture
def memory_manager(temp_memory_dir):
    """Create a MemoryManager instance with temporary directory."""
    return MemoryManager(memory_dir=temp_memory_dir)


@pytest.mark.asyncio
class TestMemoryManager:
    """Test MemoryManager functionality."""
    
    async def test_isolated_scope_basic_operations(self, memory_manager):
        """Test basic get/set operations for isolated scope."""
        # Test set and get
        await memory_manager.set("isolated", "agent1:story1", {"data": "test_value"})
        result = await memory_manager.get("isolated", "agent1:story1")
        
        assert result == {"data": "test_value"}
    
    async def test_shared_scope_basic_operations(self, memory_manager):
        """Test basic get/set operations for shared scope."""
        # Test set and get
        await memory_manager.set("shared", "global_data", {"shared": "value"})
        result = await memory_manager.get("shared", "global_data")
        
        assert result == {"shared": "value"}
    
    async def test_isolated_scope_isolation(self, memory_manager):
        """Test that isolated scope keeps data separate per agent/story."""
        # Set values for different agent/story combinations
        await memory_manager.set("isolated", "agent1:story1", {"data": "A"})
        await memory_manager.set("isolated", "agent1:story2", {"data": "B"})
        await memory_manager.set("isolated", "agent2:story1", {"data": "C"})
        
        # Verify isolation
        assert await memory_manager.get("isolated", "agent1:story1") == {"data": "A"}
        assert await memory_manager.get("isolated", "agent1:story2") == {"data": "B"}
        assert await memory_manager.get("isolated", "agent2:story1") == {"data": "C"}
        
        # Verify different agents don't share data
        assert await memory_manager.get("isolated", "agent1:story1") != await memory_manager.get("isolated", "agent2:story1")
    
    async def test_shared_scope_accessibility(self, memory_manager):
        """Test shared scope accessibility across agents."""
        # Set shared data
        await memory_manager.set("shared", "config", {"setting": "value"})
        
        # Verify it can be accessed as shared data
        result1 = await memory_manager.get("shared", "config")
        result2 = await memory_manager.get("shared", "config")
        
        assert result1 == result2 == {"setting": "value"}
    
    async def test_cache_functionality(self, memory_manager):
        """Test cache persistence and loading."""
        # Set value and verify it's in cache
        await memory_manager.set("isolated", "agent1:story1", {"cached": "data"})
        
        # Check cache stats
        stats = memory_manager.get_cache_stats()
        assert stats["cache_size"] > 0
        assert "isolated:agent1:story1" in stats["cache_keys"]
        
        # Clear cache and verify data is still retrievable from file
        memory_manager.clear_cache()
        result = await memory_manager.get("isolated", "agent1:story1")
        assert result == {"cached": "data"}
    
    async def test_file_persistence(self, memory_manager, temp_memory_dir):
        """Test that data persists to JSONL files."""
        # Set some data
        await memory_manager.set("isolated", "agent1:story1", {"persistent": "data"})
        await memory_manager.set("shared", "global", {"global": "data"})
        
        # Check files were created
        isolated_file = Path(temp_memory_dir) / "isolated" / "agent1_story1.jsonl"
        shared_file = Path(temp_memory_dir) / "shared_global.jsonl"
        
        assert isolated_file.exists()
        assert shared_file.exists()
        
        # Verify file contents
        with open(isolated_file, 'r') as f:
            line = f.readline().strip()
            entry = json.loads(line)
            assert entry["key"] == "agent1:story1"
            assert entry["value"] == {"persistent": "data"}
        
        with open(shared_file, 'r') as f:
            line = f.readline().strip()
            entry = json.loads(line)
            assert entry["key"] == "global"
            assert entry["value"] == {"global": "data"}
    
    async def test_concurrent_access(self, memory_manager):
        """Test thread-safe concurrent operations."""
        async def writer(n: int):
            await memory_manager.set("shared", "counter", n)
            return n
        
        async def reader():
            return await memory_manager.get("shared", "counter")
        
        # Run concurrent operations
        write_tasks = [writer(i) for i in range(10)]
        read_tasks = [reader() for _ in range(5)]
        
        results = await asyncio.gather(*write_tasks, *read_tasks)
        
        # Verify final value is one of the written values
        final_value = await memory_manager.get("shared", "counter")
        assert final_value in range(10)
    
    async def test_invalid_scope_handling(self, memory_manager):
        """Test error handling for invalid scopes."""
        with pytest.raises(ValueError, match="Invalid scope"):
            await memory_manager.set("invalid", "key", "value")
        
        with pytest.raises(ValueError, match="Invalid scope"):
            await memory_manager.get("invalid", "key")
    
    async def test_invalid_isolated_key_format(self, memory_manager):
        """Test error handling for invalid isolated key format."""
        with pytest.raises(ValueError, match="must contain ':' separator"):
            await memory_manager.set("isolated", "invalid_key", "value")
        
        with pytest.raises(ValueError, match="must contain ':' separator"):
            await memory_manager.get("isolated", "invalid_key")
    
    async def test_get_nonexistent_key(self, memory_manager):
        """Test retrieving non-existent keys returns None."""
        result = await memory_manager.get("isolated", "agent1:nonexistent")
        assert result is None
        
        result = await memory_manager.get("shared", "nonexistent")
        assert result is None
    
    async def test_flush_functionality(self, memory_manager, temp_memory_dir):
        """Test flush operation."""
        # Set data in cache only
        memory_manager._cache["isolated:agent1:story1"] = {"test": "data"}
        memory_manager._cache["shared:global"] = {"shared": "data"}
        
        # Flush cache
        await memory_manager.flush()
        
        # Verify files were created
        isolated_file = Path(temp_memory_dir) / "isolated" / "agent1_story1.jsonl"
        shared_file = Path(temp_memory_dir) / "shared_global.jsonl"
        
        assert isolated_file.exists()
        assert shared_file.exists()
    
    async def test_data_type_support(self, memory_manager):
        """Test support for different data types."""
        test_data = {
            "string": "test_string",
            "integer": 42,
            "float": 3.14,
            "boolean": True,
            "list": [1, 2, 3],
            "dict": {"nested": "value"},
            "null": None
        }
        
        for key, value in test_data.items():
            await memory_manager.set("shared", f"type_test_{key}", value)
            result = await memory_manager.get("shared", f"type_test_{key}")
            assert result == value
    
    async def test_append_only_behavior(self, memory_manager, temp_memory_dir):
        """Test JSONL append-only behavior."""
        # Set same key multiple times
        await memory_manager.set("shared", "updated_key", "value1")
        await memory_manager.set("shared", "updated_key", "value2")
        await memory_manager.set("shared", "updated_key", "value3")
        
        # Clear cache and reload from file
        memory_manager.clear_cache()
        result = await memory_manager.get("shared", "updated_key")
        
        # Should get latest value
        assert result == "value3"
        
        # Verify file contains all entries
        shared_file = Path(temp_memory_dir) / "shared_updated_key.jsonl"
        with open(shared_file, 'r') as f:
            lines = f.readlines()
            assert len(lines) == 3  # All writes were appended
    
    async def test_corrupted_file_handling(self, memory_manager, temp_memory_dir):
        """Test handling of corrupted JSONL files."""
        # Create a corrupted JSONL file
        corrupted_file = Path(temp_memory_dir) / "shared_corrupted.jsonl"
        corrupted_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(corrupted_file, 'w') as f:
            f.write("invalid json line\n")
            f.write('{"key": "valid", "value": "data"}\n')
        
        # Should handle corruption gracefully
        result = await memory_manager.get("shared", "corrupted")
        assert result is None  # File exists but corrupted, so no data loaded
    
    async def test_large_data_handling(self, memory_manager):
        """Test handling of larger data structures."""
        large_data = {
            "items": [f"item_{i}" for i in range(1000)],
            "metadata": {f"key_{i}": f"value_{i}" for i in range(100)}
        }
        
        await memory_manager.set("shared", "large_data", large_data)
        result = await memory_manager.get("shared", "large_data")
        
        assert result == large_data
        assert len(result["items"]) == 1000
        assert len(result["metadata"]) == 100


@pytest.mark.asyncio
class TestMemoryAPI:
    """Test memory API endpoints."""
    
    @pytest.fixture
    def mock_memory_manager(self):
        """Mock memory manager for API tests."""
        # Import the module first to ensure it's loaded
        import generated.memory_router
        with patch.object(generated.memory_router, 'memory_manager') as mock:
            yield mock
    
    async def test_get_memory_success(self, mock_memory_manager):
        """Test successful memory retrieval via API."""
        from generated.memory_router import get_memory
        
        # Mock successful get (async)
        mock_memory_manager.get = AsyncMock(return_value={"test": "data"})
        
        response = await get_memory("isolated", "agent1:story1")
        
        assert response.value == {"test": "data"}
        mock_memory_manager.get.assert_called_once_with("isolated", "agent1:story1")
    
    async def test_get_memory_not_found(self, mock_memory_manager):
        """Test memory retrieval when key not found."""
        from generated.memory_router import get_memory
        from fastapi import HTTPException
        
        # Mock key not found (async)
        mock_memory_manager.get = AsyncMock(return_value=None)
        
        with pytest.raises(HTTPException) as exc_info:
            await get_memory("isolated", "agent1:story1")
        
        assert exc_info.value.status_code == 404
        assert "Key not found" in str(exc_info.value.detail)
    
    async def test_put_memory_success(self, mock_memory_manager):
        """Test successful memory update via API."""
        from generated.memory_router import put_memory, MemoryValue
        
        # Mock successful set
        mock_memory_manager.set = AsyncMock()
        
        data = MemoryValue(value={"new": "data"})
        response = await put_memory("shared", "test_key", data)
        
        assert response.message == "Memory updated successfully"
        assert response.scope == "shared"
        assert response.key == "test_key"
        mock_memory_manager.set.assert_called_once_with("shared", "test_key", {"new": "data"})
    
    async def test_memory_stats_endpoint(self, mock_memory_manager):
        """Test memory stats endpoint."""
        from generated.memory_router import get_memory_stats
        
        mock_memory_manager.get_cache_stats.return_value = {
            "cache_size": 5,
            "lock_count": 3,
            "cache_keys": ["isolated:agent1:story1", "shared:global"]
        }
        
        response = await get_memory_stats()
        
        assert response["cache_size"] == 5
        assert response["lock_count"] == 3
        assert len(response["cache_keys"]) == 2
    
    async def test_flush_endpoint(self, mock_memory_manager):
        """Test memory flush endpoint."""
        from generated.memory_router import flush_memory
        
        mock_memory_manager.flush = AsyncMock()
        
        response = await flush_memory()
        
        assert response["message"] == "Memory flushed successfully"
        mock_memory_manager.flush.assert_called_once()
    
    async def test_clear_cache_endpoint(self, mock_memory_manager):
        """Test cache clear endpoint."""
        from generated.memory_router import clear_memory_cache
        
        response = await clear_memory_cache()
        
        assert response["message"] == "Memory cache cleared successfully"
        mock_memory_manager.clear_cache.assert_called_once()