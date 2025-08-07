"""Unit tests for BMAD preprocessing format v2.0.

These tests validate the enhanced preprocessing format with BMAD terminology
and backward compatibility with v1.0 format.
"""

import json
import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch

import sys
from pathlib import Path

# Add scripts directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))

from parser import (
    AgentMetadata, 
    parse_front_matter, 
    parse_markdown_file, 
    parse_agents_directory,
    ParsingError
)
from validate_preprocessing import (
    load_schema,
    validate_against_schema,
    validate_file_references,
    validate_agent_dependencies,
    auto_fix_common_issues
)


class TestAgentMetadataV2:
    """Test AgentMetadata model with v2.0 fields."""
    
    def test_v1_format_compatibility(self):
        """Test that v1.0 format still works."""
        metadata = AgentMetadata(
            id="simple_agent",
            description="Basic agent",
            tools=["basic_tool"],
            memory_scope="isolated"
        )
        
        assert metadata.id == "simple_agent"
        assert metadata.format_version == "1.0"
        assert not metadata.is_v2_format()
        assert metadata.persona == ""
        assert metadata.tasks == []
    
    def test_v2_format_detection(self):
        """Test v2.0 format detection with BMAD fields."""
        metadata = AgentMetadata(
            id="analyst",
            description="Business analyst",
            persona="Senior analyst with 10+ years experience",
            tasks=["analyze.md"],
            checklists=["quality.md"],
            format_version="2.0"
        )
        
        assert metadata.is_v2_format()
        assert metadata.format_version == "2.0"
        assert metadata.persona == "Senior analyst with 10+ years experience"
    
    def test_auto_v2_detection_by_fields(self):
        """Test automatic v2.0 detection based on BMAD field presence."""
        metadata = AgentMetadata(
            id="analyst",
            persona="Senior analyst"  # This should trigger v2.0 detection
        )
        
        assert metadata.is_v2_format()
    
    def test_bmad_terminology_fields(self):
        """Test all BMAD terminology fields."""
        metadata = AgentMetadata(
            id="full_agent",
            persona="Expert developer",
            tasks=["implement.md", "test.md"],
            checklists=["quality.md", "review.md"],
            templates=["report.md"],
            commands=["*implement", "*test", "*deploy"]
        )
        
        assert metadata.persona == "Expert developer"
        assert len(metadata.tasks) == 2
        assert len(metadata.checklists) == 2
        assert len(metadata.templates) == 1
        assert len(metadata.commands) == 3
        assert metadata.is_v2_format()
    
    def test_memory_scope_validation(self):
        """Test memory scope validation including namespaced scopes."""
        # Valid scopes
        for scope in ["isolated", "shared", "shared:analysis"]:
            metadata = AgentMetadata(id="test", memory_scope=scope)
            assert metadata.memory_scope == scope
        
        # Invalid scope should raise validation error
        with pytest.raises(ValueError, match="memory_scope must be"):
            AgentMetadata(id="test", memory_scope="invalid")
    
    def test_id_validation(self):
        """Test ID validation rules."""
        # Valid IDs
        for valid_id in ["analyst", "pm_reviewer", "qa-specialist", "dev123"]:
            metadata = AgentMetadata(id=valid_id)
            assert metadata.id == valid_id
        
        # Invalid IDs
        with pytest.raises(ValueError, match="Agent id is required"):
            AgentMetadata(id="")
        
        with pytest.raises(ValueError, match="Agent id is required"):
            AgentMetadata(id="   ")


class TestFrontMatterParsingV2:
    """Test front matter parsing with v2.0 format."""
    
    def test_v2_format_parsing(self):
        """Test parsing v2.0 format with BMAD fields."""
        content = """---
id: senior_analyst
description: "Senior business analyst"
persona: "Experienced analyst with domain expertise"
tasks:
  - analyze_requirements.md
  - validate_stories.md
checklists:
  - quality_checklist.md
templates:
  - story_template.md
commands:
  - "*analyze"
  - "*validate"
tools:
  - text_splitter
memory_scope: "shared:analysis"
wait_for:
  docs:
    - requirements.md
  agents:
    - architect
---

You are a senior business analyst...
"""
        
        metadata, prompt = parse_front_matter(content)
        
        assert metadata["id"] == "senior_analyst"
        assert metadata["persona"] == "Experienced analyst with domain expertise"
        assert len(metadata["tasks"]) == 2
        assert "analyze_requirements.md" in metadata["tasks"]
        assert len(metadata["checklists"]) == 1
        assert len(metadata["commands"]) == 2
        assert metadata["memory_scope"] == "shared:analysis"
        assert "requirements.md" in metadata["wait_for"]["docs"]
        assert "architect" in metadata["wait_for"]["agents"]
        assert prompt.strip() == "You are a senior business analyst..."
    
    def test_mixed_v1_v2_fields(self):
        """Test parsing with mix of v1.0 and v2.0 fields."""
        content = """---
id: hybrid_agent
description: "Hybrid agent example"
tools: ["basic_tool"]
persona: "Expert in analysis"
tasks: ["analyze.md"]
---

Hybrid agent content...
"""
        
        metadata, prompt = parse_front_matter(content)
        
        assert metadata["id"] == "hybrid_agent"
        assert metadata["tools"] == ["basic_tool"]  # v1.0 field
        assert metadata["persona"] == "Expert in analysis"  # v2.0 field
        assert metadata["tasks"] == ["analyze.md"]  # v2.0 field
    
    def test_backward_compatibility_v1(self):
        """Test that v1.0 format parses correctly."""
        content = """---
id: simple_agent
description: "Simple agent"
tools:
  - basic_tool
memory_scope: isolated
---

Simple agent content...
"""
        
        metadata, prompt = parse_front_matter(content)
        
        assert metadata["id"] == "simple_agent"
        assert metadata["tools"] == ["basic_tool"]
        assert metadata["memory_scope"] == "isolated"
        # v2.0 fields should not be present
        assert "persona" not in metadata
        assert "tasks" not in metadata


class TestMarkdownFileParsingV2:
    """Test complete markdown file parsing with v2.0 format."""
    
    def test_v2_file_parsing_with_auto_detection(self):
        """Test v2.0 file parsing with automatic version detection."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write("""---
id: test_analyst
persona: "Senior business analyst"
tasks:
  - analyze.md
checklists:
  - quality.md
---

Test analyst content...
""")
            f.flush()
            
            try:
                metadata, content = parse_markdown_file(Path(f.name))
                
                assert metadata.id == "test_analyst"
                assert metadata.format_version == "2.0"  # Auto-detected
                assert metadata.is_v2_format()
                assert metadata.persona == "Senior business analyst"
                assert "analyze.md" in metadata.tasks
                assert content.strip() == "Test analyst content..."
            finally:
                try:
                    Path(f.name).unlink()
                except PermissionError:
                    pass  # File might be locked on Windows
    
    def test_v1_file_parsing_auto_detection(self):
        """Test v1.0 file parsing with automatic version detection."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write("""---
id: simple_agent
tools:
  - basic_tool
---

Simple agent content...
""")
            f.flush()
            
            try:
                metadata, content = parse_markdown_file(Path(f.name))
                
                assert metadata.id == "simple_agent"
                assert metadata.format_version == "1.0"  # Auto-detected
                assert not metadata.is_v2_format()
                assert metadata.persona == ""
                assert metadata.tasks == []
            finally:
                try:
                    Path(f.name).unlink()
                except PermissionError:
                    pass  # File might be locked on Windows


class TestSchemaValidation:
    """Test JSON schema validation for v2.0 format."""
    
    @pytest.fixture
    def v2_schema(self):
        """Load v2.0 schema for testing."""
        return load_schema("2.0")
    
    def test_valid_v2_agent(self, v2_schema):
        """Test validation of valid v2.0 agent."""
        agent_data = {
            "id": "senior_analyst",
            "description": "Senior business analyst",
            "persona": "Experienced analyst with domain expertise",
            "tasks": ["analyze.md", "validate.md"],
            "checklists": ["quality.md"],
            "templates": ["report.md"],
            "commands": ["*analyze", "*validate"],
            "tools": ["text_splitter"],
            "memory_scope": "shared:analysis",
            "wait_for": {
                "docs": ["requirements.md"],
                "agents": ["architect"]
            },
            "parallel": False,
            "format_version": "2.0"
        }
        
        result = validate_against_schema(agent_data, v2_schema)
        assert result.success
        assert len(result.errors) == 0
    
    def test_invalid_id_format(self, v2_schema):
        """Test validation of invalid ID format."""
        agent_data = {
            "id": "123invalid",  # Invalid: starts with number
            "description": "Test agent"
        }
        
        result = validate_against_schema(agent_data, v2_schema)
        assert not result.success
        assert any("does not match" in error for error in result.errors)
    
    def test_invalid_command_format(self, v2_schema):
        """Test validation of invalid command format."""
        agent_data = {
            "id": "test_agent",
            "commands": ["analyze"]  # Invalid: missing asterisk prefix
        }
        
        result = validate_against_schema(agent_data, v2_schema)
        assert not result.success
        assert any("does not match" in error for error in result.errors)
    
    def test_persona_length_limit(self, v2_schema):
        """Test persona length limit validation."""
        agent_data = {
            "id": "test_agent",
            "persona": "x" * 201  # Invalid: exceeds 200 character limit
        }
        
        result = validate_against_schema(agent_data, v2_schema)
        assert not result.success
        assert any("is too long" in error for error in result.errors)
    
    def test_memory_scope_validation(self, v2_schema):
        """Test memory scope validation."""
        # Valid scopes
        for scope in ["isolated", "shared", "shared:namespace"]:
            agent_data = {"id": "test", "memory_scope": scope}
            result = validate_against_schema(agent_data, v2_schema)
            assert result.success, f"Valid scope '{scope}' failed validation"
        
        # Invalid scope
        agent_data = {"id": "test", "memory_scope": "invalid_scope"}
        result = validate_against_schema(agent_data, v2_schema)
        assert not result.success


class TestFileReferenceValidation:
    """Test validation of file references in v2.0 format."""
    
    def test_valid_file_references(self):
        """Test validation when all referenced files exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir)
            
            # Create referenced files
            (base_path / "tasks").mkdir()
            (base_path / "tasks" / "analyze.md").touch()
            (base_path / "checklists").mkdir() 
            (base_path / "checklists" / "quality.md").touch()
            (base_path / "templates").mkdir()
            (base_path / "templates" / "report.md").touch()
            
            agent_data = {
                "tasks": ["analyze.md"],
                "checklists": ["quality.md"],
                "templates": ["report.md"],
                "wait_for": {"docs": [], "agents": []}
            }
            
            result = validate_file_references(agent_data, base_path)
            assert result.success
            assert len(result.errors) == 0
    
    def test_missing_file_references(self):
        """Test validation when referenced files are missing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir)
            
            agent_data = {
                "tasks": ["missing_task.md"],
                "checklists": ["missing_checklist.md"],
                "templates": ["missing_template.md"],
                "wait_for": {"docs": [], "agents": []}
            }
            
            result = validate_file_references(agent_data, base_path)
            assert not result.success
            assert len(result.errors) == 3
            assert any("Task file not found" in error for error in result.errors)
            assert any("Checklist file not found" in error for error in result.errors)
            assert any("Template file not found" in error for error in result.errors)


class TestAgentDependencyValidation:
    """Test validation of inter-agent dependencies."""
    
    def test_valid_agent_dependencies(self):
        """Test validation of valid agent dependencies."""
        # Mock agent metadata
        analyst_meta = AgentMetadata(id="analyst", wait_for={"docs": [], "agents": []})
        arch_meta = AgentMetadata(id="architect", wait_for={"docs": [], "agents": ["analyst"]})
        
        all_agents = {
            "analyst": (analyst_meta, "content"),
            "architect": (arch_meta, "content")
        }
        
        result = validate_agent_dependencies(all_agents)
        assert result.success
        assert len(result.errors) == 0
    
    def test_missing_agent_dependency(self):
        """Test validation with missing agent dependency."""
        arch_meta = AgentMetadata(id="architect", wait_for={"docs": [], "agents": ["missing_agent"]})
        
        all_agents = {
            "architect": (arch_meta, "content")
        }
        
        result = validate_agent_dependencies(all_agents)
        assert not result.success
        assert any("depends on unknown agent" in error for error in result.errors)
    
    def test_circular_dependency_detection(self):
        """Test detection of circular dependencies."""
        self_dep_meta = AgentMetadata(id="circular", wait_for={"docs": [], "agents": ["circular"]})
        
        all_agents = {
            "circular": (self_dep_meta, "content")
        }
        
        result = validate_agent_dependencies(all_agents)
        assert not result.success
        assert any("circular dependency" in error for error in result.errors)


class TestBackwardCompatibility:
    """Test backward compatibility between v1.0 and v2.0 formats."""
    
    def test_mixed_version_directory(self):
        """Test parsing directory with mixed v1.0 and v2.0 files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            agents_dir = Path(temp_dir) / "agents"
            agents_dir.mkdir()
            
            # Create v1.0 agent
            v1_file = agents_dir / "simple.md"
            v1_file.write_text("""---
id: simple_agent
tools: ["basic_tool"]
---

Simple v1.0 agent content.
""")
            
            # Create v2.0 agent
            v2_file = agents_dir / "advanced.md"
            v2_file.write_text("""---
id: advanced_agent
persona: "Expert analyst"
tasks: ["analyze.md"]
commands: ["*analyze"]
---

Advanced v2.0 agent content.
""")
            
            agents = parse_agents_directory(agents_dir)
            
            assert len(agents) == 2
            
            # Check v1.0 agent
            simple_meta, simple_content = agents["simple_agent"]
            assert simple_meta.format_version == "1.0"
            assert not simple_meta.is_v2_format()
            assert simple_meta.persona == ""
            
            # Check v2.0 agent
            advanced_meta, advanced_content = agents["advanced_agent"]
            assert advanced_meta.format_version == "2.0" 
            assert advanced_meta.is_v2_format()
            assert advanced_meta.persona == "Expert analyst"


class TestAutoFix:
    """Test auto-fix functionality for common formatting issues."""
    
    def test_auto_fix_unquoted_strings(self):
        """Test auto-fixing unquoted string values in YAML.
        
        Following KISS principle: Only fix the most critical issue (unquoted id).
        Complex YAML fixes should be done manually with clear error messages.
        """
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write("""---
id: test_agent
description: This should be quoted
persona: Expert analyst without quotes
---

Agent content...
""")
            f.flush()
            
            try:
                # Auto-fix should only fix the id field (KISS principle)
                result = auto_fix_common_issues(Path(f.name))
                assert result  # Should return True indicating fixes were made
                
                # Read back and verify only id was quoted (KISS: one simple fix)
                content = Path(f.name).read_text()
                assert 'id: "test_agent"' in content
                # Description remains unchanged - user fixes manually with help from error messages
                assert 'description: This should be quoted' in content
                
            finally:
                try:
                    Path(f.name).unlink()
                except PermissionError:
                    pass  # File might be locked on Windows


class TestCookbookPatternIntegration:
    """Test integration with PocketFlow cookbook patterns."""
    
    def test_stateless_pattern_mapping(self):
        """Test mapping of v2.0 fields to stateless execution pattern."""
        metadata = AgentMetadata(
            id="stateless_agent",
            persona="Expert analyst",
            tasks=["process.md"],
            checklists=["validate.md"],
            format_version="2.0"
        )
        
        # Should map to prep/exec/post pattern
        assert metadata.is_v2_format()
        assert metadata.persona  # Used in prep() phase
        assert metadata.tasks    # Loaded in prep() phase  
        assert metadata.checklists  # Applied in post() phase
    
    def test_communication_pattern_mapping(self):
        """Test mapping of commands to flow transitions."""
        metadata = AgentMetadata(
            id="interactive_agent",
            commands=["*analyze", "*validate", "*report"],
            format_version="2.0"
        )
        
        # Commands should map to flow actions
        assert len(metadata.commands) == 3
        assert all(cmd.startswith("*") for cmd in metadata.commands)
        # These would become flow transitions like: agent - "analyze" >> next_node
    
    def test_supervisor_pattern_mapping(self):
        """Test mapping of checklists to supervisor validation.""" 
        metadata = AgentMetadata(
            id="supervised_agent",
            checklists=["quality.md", "completeness.md"],
            format_version="2.0"
        )
        
        # Checklists should enable supervisor pattern
        assert len(metadata.checklists) == 2
        # These would be used by SupervisorNode for validation


# Integration test
def test_full_v2_workflow():
    """Integration test of complete v2.0 workflow."""
    with tempfile.TemporaryDirectory() as temp_dir:
        base_path = Path(temp_dir)
        agents_dir = base_path / "agents"
        agents_dir.mkdir()
        
        # Create supporting files
        (base_path / "tasks").mkdir()
        (base_path / "tasks" / "analyze.md").write_text("# Analysis Task\nDetailed analysis steps...")
        (base_path / "checklists").mkdir()
        (base_path / "checklists" / "quality.md").write_text("# Quality Checklist\n- Check completeness...")
        
        # Create v2.0 agent file
        agent_file = agents_dir / "analyst.md"
        agent_file.write_text("""---
id: senior_analyst
description: "Senior business analyst for requirements analysis"
persona: "Senior business analyst with 10+ years experience"
tasks:
  - analyze.md
checklists:
  - quality.md
commands:
  - "*analyze"
  - "*validate"
tools:
  - text_splitter
memory_scope: "shared:analysis"
format_version: "2.0"
---

You are a senior business analyst responsible for analyzing requirements and creating detailed specifications.

Follow the structured approach defined in your task files and ensure all outputs pass quality validation.
""")
        
        # Parse the directory
        agents = parse_agents_directory(agents_dir)
        
        # Verify parsing
        assert len(agents) == 1
        metadata, content = agents["senior_analyst"]
        
        # Verify v2.0 format detection and fields
        assert metadata.is_v2_format()
        assert metadata.format_version == "2.0"
        assert metadata.persona == "Senior business analyst with 10+ years experience"
        assert "analyze.md" in metadata.tasks
        assert "quality.md" in metadata.checklists
        assert "*analyze" in metadata.commands
        assert metadata.memory_scope == "shared:analysis"
        
        # Verify content parsing
        assert "You are a senior business analyst" in content
        
        # Validate against schema
        schema = load_schema("2.0")
        result = validate_against_schema(metadata.model_dump(), schema)
        assert result.success
        
        # Validate file references
        file_result = validate_file_references(metadata.model_dump(), base_path)
        assert file_result.success


if __name__ == "__main__":
    pytest.main([__file__, "-v"])