"""
Example unit test file demonstrating test structure and patterns.
"""

import pytest


def test_example_addition():
    """Test that basic addition works."""
    assert 1 + 1 == 2


def test_example_string():
    """Test string operations."""
    text = "hello world"
    assert text.upper() == "HELLO WORLD"
    assert text.split() == ["hello", "world"]


@pytest.mark.asyncio
async def test_example_async():
    """Test async function example."""
    import asyncio
    
    async def async_function():
        await asyncio.sleep(0.01)
        return "completed"
    
    result = await async_function()
    assert result == "completed"


class TestExampleClass:
    """Example test class for grouping related tests."""
    
    def test_list_operations(self):
        """Test list operations."""
        items = [1, 2, 3]
        items.append(4)
        assert items == [1, 2, 3, 4]
        assert len(items) == 4
    
    def test_dict_operations(self):
        """Test dictionary operations."""
        data = {"key": "value"}
        data["new_key"] = "new_value"
        assert "new_key" in data
        assert data.get("missing", "default") == "default"


@pytest.mark.parametrize("input_val,expected", [
    (2, 4),
    (3, 9),
    (4, 16),
    (5, 25),
])
def test_square_function(input_val, expected):
    """Test square function with multiple inputs."""
    def square(x):
        return x * x
    
    assert square(input_val) == expected