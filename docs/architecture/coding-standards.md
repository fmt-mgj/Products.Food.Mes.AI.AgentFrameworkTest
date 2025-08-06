# BMAD → PocketFlow Generator & Runtime - Coding Standards

## Python Coding Standards

### General Principles

1. **Readability First** - Code is read far more often than written
2. **Explicit over Implicit** - Clear intent over clever shortcuts
3. **Consistency** - Follow existing patterns in the codebase
4. **KISS Principle** - Keep implementations simple and straightforward
5. **DRY with Pragmatism** - Avoid repetition, but not at the cost of clarity

### Code Style Guide

#### Formatting

- **Style Guide**: PEP 8 compliance enforced via Black and Ruff
- **Line Length**: Maximum 88 characters (Black default)
- **Indentation**: 4 spaces (no tabs)
- **Import Order**: 
  1. Standard library imports
  2. Third-party imports
  3. Local application imports
  - Each group alphabetically sorted

#### Naming Conventions

```python
# Classes: PascalCase
class AgentExecutor:
    pass

# Functions/Methods: snake_case
def parse_markdown_file():
    pass

# Constants: UPPER_SNAKE_CASE
MAX_RETRY_ATTEMPTS = 3
DEFAULT_TIMEOUT = 30

# Private methods: Leading underscore
def _internal_helper():
    pass

# Module-level private: Leading underscore
_cache = {}
```

#### Type Hints

All functions should include type hints for parameters and return values:

```python
from typing import Optional, List, Dict, Any

async def execute_agent(
    agent_id: str,
    context: Dict[str, Any],
    timeout: Optional[int] = None
) -> Dict[str, Any]:
    """Execute an agent with given context."""
    pass
```

### Async/Await Patterns

```python
# Always use async/await for I/O operations
async def read_document(doc_id: str) -> str:
    async with aiofiles.open(f"docs/{doc_id}.md", "r") as f:
        return await f.read()

# Use asyncio.gather for parallel operations
async def execute_parallel_agents(agents: List[Agent]) -> List[Dict]:
    results = await asyncio.gather(
        *[agent.execute() for agent in agents],
        return_exceptions=True
    )
    return results

# Proper async context managers
async with asyncio.TaskGroup() as tg:
    for task in tasks:
        tg.create_task(process_task(task))
```

### Error Handling

```python
# Define specific exception classes
class BMADError(Exception):
    """Base exception for BMAD-related errors."""
    pass

class ParsingError(BMADError):
    """Raised when BMAD file parsing fails."""
    def __init__(self, file: str, line: int, message: str):
        self.file = file
        self.line = line
        super().__init__(f"{file}:{line}: {message}")

# Use explicit error handling
try:
    result = await call_llm(prompt)
except RateLimitError:
    # Handle rate limiting specifically
    await asyncio.sleep(backoff_time)
    raise
except Exception as e:
    logger.error(f"Unexpected error in LLM call: {e}")
    raise

# Never use bare except
# Bad: except:
# Good: except Exception as e:
```

### Documentation Standards

#### Docstrings

Use Google-style docstrings for all public functions and classes:

```python
def parse_front_matter(content: str) -> Dict[str, Any]:
    """Parse YAML front matter from Markdown content.
    
    Args:
        content: Raw Markdown content with optional YAML front matter.
        
    Returns:
        Dictionary containing parsed metadata.
        
    Raises:
        ParsingError: If YAML parsing fails.
        
    Example:
        >>> metadata = parse_front_matter("---\nid: test\n---\n# Content")
        >>> print(metadata['id'])
        'test'
    """
    pass
```

#### Comments

```python
# Use comments sparingly - code should be self-documenting
# Comments should explain WHY, not WHAT

# Good: Cache results to avoid rate limiting on repeated calls
cached_results = {}

# Bad: Set cached_results to empty dict
cached_results = {}

# Use TODO comments for future work
# TODO: Implement Redis backend for distributed caching
```

### Testing Standards

#### Test Organization

```python
# Test file naming: test_<module>.py
# Test class naming: Test<ClassName>
# Test method naming: test_<scenario>_<expected_outcome>

class TestAgentExecutor:
    def test_execute_with_valid_input_returns_success(self):
        """Test that valid input produces successful execution."""
        pass
        
    def test_execute_with_missing_deps_raises_error(self):
        """Test that missing dependencies raise DependencyError."""
        pass
```

#### Test Structure (AAA Pattern)

```python
def test_agent_execution():
    # Arrange
    agent = Agent(id="test", prompt="Test prompt")
    context = {"story_id": "S-123"}
    
    # Act
    result = agent.execute(context)
    
    # Assert
    assert result["status"] == "success"
    assert "output" in result
```

#### Fixtures and Mocking

```python
import pytest
from unittest.mock import AsyncMock, patch

@pytest.fixture
async def mock_llm():
    """Fixture providing mocked LLM client."""
    with patch("app.llm_client") as mock:
        mock.complete = AsyncMock(return_value="Test response")
        yield mock

async def test_with_mock_llm(mock_llm):
    result = await process_with_llm("test")
    mock_llm.complete.assert_called_once_with("test")
```

### Performance Guidelines

#### Memory Management

```python
# Use generators for large datasets
def read_large_file(path: str):
    with open(path) as f:
        for line in f:
            yield line.strip()

# Clear caches explicitly when done
cache = {}
try:
    # Use cache
    pass
finally:
    cache.clear()
```

#### Optimization Principles

1. **Profile First** - Never optimize without profiling
2. **Async I/O** - Use async for all I/O operations
3. **Batch Operations** - Group database/API calls
4. **Cache Wisely** - Cache expensive computations, not everything
5. **Lazy Loading** - Load resources only when needed

### Security Standards

#### Input Validation

```python
from pydantic import BaseModel, validator
import re

class DocumentId(BaseModel):
    id: str
    
    @validator("id")
    def validate_id(cls, v):
        # Prevent path traversal
        if ".." in v or "/" in v or "\\" in v:
            raise ValueError("Invalid document ID")
        # Allow only alphanumeric and dash
        if not re.match(r"^[a-zA-Z0-9-]+$", v):
            raise ValueError("Document ID must be alphanumeric")
        return v
```

#### Secret Management

```python
import os
from typing import Optional

def get_secret(key: str) -> Optional[str]:
    """Get secret from environment variable.
    
    Never:
    - Log secrets
    - Include secrets in error messages
    - Store secrets in code
    """
    value = os.environ.get(key)
    if not value:
        logger.warning(f"Secret {key} not found")  # Don't log the value!
    return value
```

### File Organization

#### Module Structure

```python
"""Module docstring explaining purpose.

This module handles BMAD file parsing and metadata extraction.
"""

# Standard library imports
import asyncio
import json
from pathlib import Path

# Third-party imports
import yaml
from pydantic import BaseModel

# Local imports
from .errors import ParsingError
from .models import AgentMetadata

# Constants
DEFAULT_TIMEOUT = 30

# Classes and functions follow...
```

#### Generated Code Standards

Generated code should:
1. Include header comment indicating it's generated
2. Pass all linting without suppressions
3. Use consistent formatting via Black
4. Include minimal inline documentation (self-documenting)

```python
# Generated by BMAD → PocketFlow Generator
# Do not edit this file directly - modify BMAD sources instead
# Generated at: 2024-01-15 10:30:45 UTC

from pocketflow import Node, Flow
# ... rest of generated code
```

### Code Review Checklist

Before submitting code:

- [ ] Passes `black --check`
- [ ] Passes `ruff check`
- [ ] All functions have type hints
- [ ] Public functions have docstrings
- [ ] Tests written for new functionality
- [ ] No hardcoded secrets or paths
- [ ] Error handling is explicit
- [ ] Async/await used for I/O operations
- [ ] Performance implications considered
- [ ] Security validations in place

### Tool Configuration

#### pyproject.toml

```toml
[tool.black]
line-length = 88
target-version = ['py310']

[tool.ruff]
line-length = 88
select = ["E", "F", "I", "N", "W"]
ignore = ["E501"]  # Line length handled by Black

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
python_files = "test_*.py"
```

#### Pre-commit Configuration

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/psf/black
    rev: 23.12.0
    hooks:
      - id: black
  - repo: https://github.com/charliermarsh/ruff-pre-commit
    rev: v0.1.8
    hooks:
      - id: ruff
```

## Enforcement

These standards are enforced through:

1. **Automated Formatting** - Black on save/commit
2. **Linting** - Ruff in CI/CD pipeline
3. **Code Review** - Manual review against checklist
4. **Pre-commit Hooks** - Automatic validation before commit
5. **CI/CD Gates** - Build fails if standards not met

---

*These coding standards are living guidelines. Propose changes through pull requests with clear justification.*