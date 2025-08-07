"""
Pytest configuration and shared fixtures for all tests.
"""

import pytest
import asyncio
from pathlib import Path
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def test_data_dir():
    """Path to test data directory."""
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def temp_bmad_dir(tmp_path):
    """Temporary BMAD directory for testing."""
    bmad_dir = tmp_path / "preprocessing"
    bmad_dir.mkdir()
    (bmad_dir / "agents").mkdir()
    (bmad_dir / "checklists").mkdir()
    (bmad_dir / "workflows").mkdir()
    return bmad_dir


@pytest.fixture
def sample_agent_content():
    """Sample BMAD agent content for testing."""
    return """---
id: test_agent
title: Test Agent
tools:
  - search
  - memory
memory_scope: isolated
---

# Test Agent

This is a test agent for unit testing."""