"""Unit tests for BMAD Markdown parser."""

from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from scripts.parser import (
    AgentMetadata,
    ParsingError,
    parse_agents_directory,
    parse_front_matter,
    parse_markdown_file,
)


class TestAgentMetadata:
    """Test AgentMetadata model validation."""

    def test_valid_metadata(self):
        """Test creating valid metadata object."""
        metadata = AgentMetadata(
            id="test_agent",
            description="Test agent",
            tools=["search", "write"],
            memory_scope="isolated",
            wait_for={"docs": ["prd.md"], "agents": ["analyst"]},
            parallel=True,
        )
        assert metadata.id == "test_agent"
        assert metadata.description == "Test agent"
        assert metadata.tools == ["search", "write"]
        assert metadata.memory_scope == "isolated"
        assert metadata.parallel is True

    def test_minimal_metadata(self):
        """Test creating metadata with only required fields."""
        metadata = AgentMetadata(id="minimal")
        assert metadata.id == "minimal"
        assert metadata.description == ""
        assert metadata.tools == []
        assert metadata.memory_scope == "isolated"
        assert metadata.wait_for == {"docs": [], "agents": []}
        assert metadata.parallel is False

    def test_invalid_memory_scope(self):
        """Test validation fails for invalid memory scope."""
        with pytest.raises(ValueError, match="memory_scope must be"):
            AgentMetadata(id="test", memory_scope="invalid")

    def test_empty_id_fails(self):
        """Test validation fails for empty id."""
        with pytest.raises(ValueError, match="Agent id is required"):
            AgentMetadata(id="")

    def test_whitespace_id_trimmed(self):
        """Test id gets trimmed of whitespace."""
        metadata = AgentMetadata(id="  test_agent  ")
        assert metadata.id == "test_agent"


class TestParseFrontMatter:
    """Test YAML front matter parsing."""

    def test_parse_valid_front_matter(self):
        """Test parsing valid YAML front matter."""
        content = """---
id: test_agent
description: Test agent for parsing
tools: [search, write]
memory_scope: isolated
---

# Agent Prompt

This is the actual markdown content.
"""
        metadata, remaining = parse_front_matter(content)

        assert metadata["id"] == "test_agent"
        assert metadata["description"] == "Test agent for parsing"
        assert metadata["tools"] == ["search", "write"]
        assert metadata["memory_scope"] == "isolated"
        assert remaining.startswith("# Agent Prompt")
        assert "This is the actual markdown content." in remaining

    def test_parse_no_front_matter(self):
        """Test content without front matter."""
        content = """# Agent Prompt

This is just markdown content.
"""
        metadata, remaining = parse_front_matter(content)

        assert metadata == {}
        assert remaining.strip() == content.strip()

    def test_parse_empty_front_matter(self):
        """Test content with empty front matter."""
        content = """---
---

# Agent Content
"""
        metadata, remaining = parse_front_matter(content)

        assert metadata == {}
        assert remaining.strip() == "# Agent Content"

    def test_parse_incomplete_front_matter(self):
        """Test content with incomplete front matter (no closing ---)."""
        content = """---
id: test_agent
description: Test

# This looks like content but no closing delimiter
"""
        metadata, remaining = parse_front_matter(content)

        assert metadata == {}
        assert remaining.strip() == content.strip()

    def test_parse_invalid_yaml(self):
        """Test content with invalid YAML in front matter."""
        content = """---
id: test_agent
invalid_yaml: [unclosed list
---

# Content
"""
        with pytest.raises(ParsingError, match="Invalid YAML"):
            parse_front_matter(content)


class TestParseMarkdownFile:
    """Test parsing individual Markdown files."""

    def test_parse_valid_file(self):
        """Test parsing a valid BMAD file."""
        content = """---
id: analyst
description: Analyzes requirements
tools: [search, read]
memory_scope: shared
parallel: false
---

# Analyst Agent

You are an expert analyst...
"""

        with TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "analyst.md"
            file_path.write_text(content, encoding="utf-8")

            metadata, prompt = parse_markdown_file(file_path)

            assert metadata.id == "analyst"
            assert metadata.description == "Analyzes requirements"
            assert metadata.tools == ["search", "read"]
            assert metadata.memory_scope == "shared"
            assert metadata.parallel is False
            assert prompt.startswith("# Analyst Agent")

    def test_parse_file_no_front_matter(self):
        """Test parsing file without front matter uses filename as id."""
        content = """# Developer Agent

You are a developer...
"""

        with TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "developer.md"
            file_path.write_text(content, encoding="utf-8")

            metadata, prompt = parse_markdown_file(file_path)

            assert metadata.id == "developer"
            assert metadata.description == ""
            assert prompt.startswith("# Developer Agent")

    def test_parse_nonexistent_file(self):
        """Test parsing nonexistent file raises error."""
        file_path = Path("/nonexistent/path/file.md")

        with pytest.raises(ParsingError, match="Cannot read file"):
            parse_markdown_file(file_path)

    def test_parse_file_with_validation_error(self):
        """Test parsing file with invalid metadata."""
        content = """---
id: ""
memory_scope: invalid
---

# Content
"""

        with TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "invalid.md"
            file_path.write_text(content, encoding="utf-8")

            with pytest.raises(ParsingError, match="Parsing failed"):
                parse_markdown_file(file_path)


class TestParseAgentsDirectory:
    """Test parsing entire agents directory."""

    def test_parse_valid_directory(self):
        """Test parsing directory with valid agent files."""

        files = {
            "analyst.md": """---
id: analyst
description: Analyzes requirements
tools: [search]
---

# Analyst
""",
            "developer.md": """---
id: developer
description: Develops code
tools: [write, test]
---

# Developer
""",
            "reviewer.md": """# Reviewer

Simple agent without front matter.
""",
        }

        with TemporaryDirectory() as temp_dir:
            dir_path = Path(temp_dir)

            for filename, content in files.items():
                file_path = dir_path / filename
                file_path.write_text(content, encoding="utf-8")

            agents = parse_agents_directory(dir_path)

            assert len(agents) == 3
            assert "analyst" in agents
            assert "developer" in agents
            assert "reviewer" in agents

            # Check analyst metadata
            analyst_meta, analyst_prompt = agents["analyst"]
            assert analyst_meta.description == "Analyzes requirements"
            assert analyst_meta.tools == ["search"]

            # Check reviewer uses filename as id
            reviewer_meta, _ = agents["reviewer"]
            assert reviewer_meta.id == "reviewer"
            assert reviewer_meta.description == ""

    def test_parse_empty_directory(self):
        """Test parsing empty directory returns empty dict."""
        with TemporaryDirectory() as temp_dir:
            dir_path = Path(temp_dir)

            agents = parse_agents_directory(dir_path)

            assert agents == {}

    def test_parse_directory_no_md_files(self):
        """Test parsing directory with no .md files."""
        with TemporaryDirectory() as temp_dir:
            dir_path = Path(temp_dir)

            # Create some non-md files
            (dir_path / "readme.txt").write_text("Not markdown")
            (dir_path / "config.yaml").write_text("key: value")

            agents = parse_agents_directory(dir_path)

            assert agents == {}

    def test_parse_nonexistent_directory(self):
        """Test parsing nonexistent directory raises error."""
        dir_path = Path("/nonexistent/directory")

        with pytest.raises(ParsingError, match="Directory does not exist"):
            parse_agents_directory(dir_path)

    def test_parse_file_instead_of_directory(self):
        """Test parsing file instead of directory raises error."""
        with TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "not_a_dir.txt"
            file_path.write_text("content")

            with pytest.raises(ParsingError, match="Path is not a directory"):
                parse_agents_directory(file_path)

    def test_parse_directory_with_duplicate_ids(self):
        """Test parsing directory with duplicate agent IDs."""

        files = {
            "agent1.md": """---
id: duplicate
description: First agent
---

# Agent 1
""",
            "agent2.md": """---
id: duplicate
description: Second agent
---

# Agent 2
""",
        }

        with TemporaryDirectory() as temp_dir:
            dir_path = Path(temp_dir)

            for filename, content in files.items():
                file_path = dir_path / filename
                file_path.write_text(content, encoding="utf-8")

            # Should not fail but log warning
            agents = parse_agents_directory(dir_path)

            assert len(agents) == 1  # Second one overwrites first
            assert agents["duplicate"][0].description == "Second agent"

    def test_parse_directory_with_invalid_file(self):
        """Test parsing directory continues with invalid files."""

        files = {
            "valid.md": """---
id: valid_agent
---

# Valid Agent
""",
            "invalid.md": """---
id: ""
memory_scope: invalid
---

# Invalid Agent
""",
        }

        with TemporaryDirectory() as temp_dir:
            dir_path = Path(temp_dir)

            for filename, content in files.items():
                file_path = dir_path / filename
                file_path.write_text(content, encoding="utf-8")

            # Should continue parsing valid files
            agents = parse_agents_directory(dir_path)

            assert len(agents) == 1
            assert "valid_agent" in agents


class TestEdgeCases:
    """Test edge cases and special scenarios."""

    def test_unicode_content(self):
        """Test parsing files with Unicode content."""
        content = """---
id: unicode_agent
description: Agent with émojis 🤖 and ünïcödé
---

# Agent with Unicode

This agent handles émojis 🚀 and special characters: àáâãäåæçèéêë
"""

        with TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "unicode.md"
            file_path.write_text(content, encoding="utf-8")

            metadata, prompt = parse_markdown_file(file_path)

            assert "émojis 🤖" in metadata.description
            assert "🚀" in prompt

    def test_very_large_file(self):
        """Test parsing very large file doesn't fail."""
        large_content = "# Large Agent\n\n" + "This is content. " * 10000

        with TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "large.md"
            file_path.write_text(large_content, encoding="utf-8")

            metadata, prompt = parse_markdown_file(file_path)

            assert metadata.id == "large"
            assert len(prompt) > 100000

    def test_complex_yaml_structure(self):
        """Test parsing complex YAML front matter."""
        content = """---
id: complex_agent
description: |
  Multi-line description
  with special characters: @#$%
tools:
  - search
  - write
  - complex_tool
wait_for:
  docs:
    - "document with spaces.md"
    - "path/to/nested/doc.md"
  agents:
    - agent_one
    - agent_two
memory_scope: shared
parallel: true
custom_field: "Should be ignored in validation but preserved"
---

# Complex Agent

Content here.
"""

        with TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "complex.md"
            file_path.write_text(content, encoding="utf-8")

            metadata, prompt = parse_markdown_file(file_path)

            assert "Multi-line description" in metadata.description
            assert "complex_tool" in metadata.tools
            assert "document with spaces.md" in metadata.wait_for["docs"]
            assert metadata.parallel is True
