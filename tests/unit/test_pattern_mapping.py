"""Tests for cookbook pattern mapping and integration.

Tests the integration of PocketFlow cookbook patterns into generated BMAD agents,
ensuring compliance with established patterns from the cookbook.
"""

import asyncio
import pytest
import yaml
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
from typing import Dict, Any

# Import the classes we need to test - KISS: direct imports from scripts
import sys
scripts_path = Path(__file__).parent.parent.parent / "scripts"
if str(scripts_path) not in sys.path:
    sys.path.insert(0, str(scripts_path))
    
from generator import Generator
from parser import AgentMetadata


class TestStatelessPatternMapping:
    """Test stateless execution patterns from pocketflow-structured-output."""
    
    def test_stateless_pattern_generation(self):
        """Test that agents follow stateless Node patterns."""
        # Create test agent metadata
        metadata = AgentMetadata(
            id="test_agent",
            description="Test agent for stateless patterns",
            tools=[],
            memory_scope="isolated",
            wait_for={"docs": [], "agents": []},
            parallel=False
        )
        
        prompt_content = "You are a test agent. Process the input and provide analysis."
        
        # Create generator and render agent
        template_dir = Path(__file__).parent.parent.parent / "scripts" / "templates"
        generator = Generator(template_dir)
        
        generated_code = generator.render_agent_node(metadata, prompt_content)
        
        # Verify cookbook pattern compliance
        assert "from pocketflow import Node" in generated_code
        assert "import yaml" in generated_code
        assert "class TestAgentNode(Node):" in generated_code
        assert "def prep(self, shared):" in generated_code
        assert "def exec(self, prep_res):" in generated_code
        assert "def post(self, shared, prep_res, exec_res):" in generated_code
        
        # Verify structured output pattern
        assert "```yaml" in generated_code
        assert "thinking:" in generated_code
        assert "result:" in generated_code
        assert "confidence:" in generated_code
        assert "yaml.safe_load" in generated_code
        
        # Verify error handling pattern
        assert "def exec_fallback(self, prep_res, exc):" in generated_code
        assert "max_retries=3" in generated_code
    
    def test_async_pattern_generation(self):
        """Test async pattern generation for parallel agents."""
        metadata = AgentMetadata(
            id="async_agent",
            description="Async test agent",
            tools=[],
            memory_scope="shared",
            wait_for={"docs": [], "agents": []},
            parallel=True
        )
        
        prompt_content = "You are an async test agent."
        
        template_dir = Path(__file__).parent.parent.parent / "scripts" / "templates"
        generator = Generator(template_dir)
        
        generated_code = generator.render_agent_node(metadata, prompt_content)
        
        # Verify async patterns
        assert "from pocketflow import Node, AsyncNode" in generated_code
        assert "class AsyncAgentNode(AsyncNode):" in generated_code
        assert "async def exec_async(self, prep_res):" in generated_code
        assert "async def post_async(self, shared, prep_res, exec_res):" in generated_code
        assert "await call_llm_async" in generated_code
    
    def test_dependency_checking_pattern(self):
        """Test external control pattern for agent dependencies."""
        metadata = AgentMetadata(
            id="dependent_agent",
            description="Agent with dependencies",
            tools=[],
            memory_scope="shared",
            wait_for={"docs": [], "agents": ["analyzer", "summarizer"]},
            parallel=False
        )
        
        prompt_content = "You are a dependent agent."
        
        template_dir = Path(__file__).parent.parent.parent / "scripts" / "templates"
        generator = Generator(template_dir)
        
        generated_code = generator.render_agent_node(metadata, prompt_content)
        
        # Verify dependency checking - updated to match new JSON format
        assert 'dependencies = ["analyzer", "summarizer"]' in generated_code
        assert "for dependency in dependencies:" in generated_code
        assert "raise RuntimeError(f\"Dependency not met:" in generated_code
        assert '"analyzer": shared.get("analyzer_result", None)' in generated_code
        assert '"summarizer": shared.get("summarizer_result", None)' in generated_code
    
    def test_memory_scoping_pattern(self):
        """Test memory scoping patterns from pocketflow-chat-memory."""
        # Test isolated memory scope
        metadata_isolated = AgentMetadata(
            id="isolated_agent",
            description="Agent with isolated memory",
            tools=[],
            memory_scope="isolated",
            wait_for={"docs": [], "agents": []},
            parallel=False
        )
        
        template_dir = Path(__file__).parent.parent.parent / "scripts" / "templates"
        generator = Generator(template_dir)
        
        generated_code = generator.render_agent_node(metadata_isolated, "test prompt")
        
        # Verify isolated memory pattern
        assert 'memory_key = f"isolated_agent_memory"' in generated_code
        
        # Test shared memory scope
        metadata_shared = AgentMetadata(
            id="shared_agent",
            description="Agent with shared memory",
            tools=[],
            memory_scope="shared",
            wait_for={"docs": [], "agents": []},
            parallel=False
        )
        
        generated_code = generator.render_agent_node(metadata_shared, "test prompt")
        
        # Verify shared memory pattern
        assert 'memory_key = "shared_memory"' in generated_code
    
    def test_structured_output_validation(self):
        """Test structured output validation following supervisor patterns."""
        metadata = AgentMetadata(
            id="test_validator",
            description="Test validation agent",
            tools=[],
            memory_scope="shared",
            wait_for={"docs": [], "agents": []},
            parallel=False
        )
        
        template_dir = Path(__file__).parent.parent.parent / "scripts" / "templates"
        generator = Generator(template_dir)
        
        generated_code = generator.render_agent_node(metadata, "Test validation")
        
        # Verify validation patterns are present in generated code
        assert "assert structured_result is not None" in generated_code
        assert 'assert "result" in structured_result' in generated_code
        assert 'assert "confidence" in structured_result' in generated_code
        assert "yaml.safe_load" in generated_code
    
    def test_error_fallback_pattern(self):
        """Test error handling and fallback patterns."""
        metadata = AgentMetadata(
            id="fallback_agent",
            description="Agent with fallback handling",
            tools=[],
            memory_scope="shared",
            wait_for={"docs": [], "agents": []},
            parallel=False
        )
        
        template_dir = Path(__file__).parent.parent.parent / "scripts" / "templates"
        generator = Generator(template_dir)
        
        generated_code = generator.render_agent_node(metadata, "test prompt")
        
        # Verify fallback pattern
        assert "def exec_fallback(self, prep_res, exc):" in generated_code
        assert '"next_action": "error"' in generated_code
        assert '"confidence": 0.1' in generated_code
        assert "Error occurred:" in generated_code


class TestExternalControlPattern:
    """Test external control patterns from pocketflow-communication."""
    
    def test_dependency_resolution(self):
        """Test that agents properly check dependencies before execution."""
        metadata = AgentMetadata(
            id="controller",
            description="Controller agent",
            tools=[],
            memory_scope="shared",
            wait_for={"docs": [], "agents": ["input_processor", "validator"]},
            parallel=False
        )
        
        template_dir = Path(__file__).parent.parent.parent / "scripts" / "templates"
        generator = Generator(template_dir)
        
        generated_code = generator.render_agent_node(metadata, "control prompt")
        
        # Verify dependency checking logic
        assert "input_processor" in generated_code
        assert "validator" in generated_code
        assert "RuntimeError" in generated_code
        assert "Dependency not met" in generated_code
    
    def test_shared_store_communication(self):
        """Test shared store communication patterns."""
        metadata = AgentMetadata(
            id="communicator",
            description="Communication test agent",
            tools=[],
            memory_scope="shared",
            wait_for={"docs": [], "agents": []},
            parallel=False
        )
        
        template_dir = Path(__file__).parent.parent.parent / "scripts" / "templates"
        generator = Generator(template_dir)
        
        generated_code = generator.render_agent_node(metadata, "test")
        
        # Verify shared store patterns
        assert 'shared["communicator_result"]' in generated_code
        assert 'shared["last_result"]' in generated_code
        assert "shared_memory" in generated_code
    
    def test_orchestrator_status_tracking(self):
        """Test orchestrator status tracking in FastAPI app."""
        agents = {
            "test_agent": (AgentMetadata(
                id="test_agent",
                description="Test agent",
                tools=[],
                memory_scope="shared",
                wait_for={"docs": [], "agents": []},
                parallel=False
            ), "Test prompt")
        }
        
        template_dir = Path(__file__).parent.parent.parent / "scripts" / "templates"
        generator = Generator(template_dir)
        
        generated_code = generator.render_fastapi_app(agents)
        
        # Verify orchestrator status tracking patterns
        assert "orchestrator_state" in generated_code
        assert "update_orchestrator_state" in generated_code
        assert "execution_id" in generated_code
        assert "/orchestrator/status/" in generated_code
        assert "/orchestrator/list" in generated_code
        assert "StatusResponse" in generated_code
    
    def test_external_control_integration(self):
        """Test complete external control integration."""
        # Test agent with dependencies
        dependent_agent = AgentMetadata(
            id="dependent",
            description="Agent with dependencies",
            tools=[],
            memory_scope="shared", 
            wait_for={"docs": [], "agents": ["prerequisite"]},
            parallel=False
        )
        
        agents = {
            "prerequisite": (AgentMetadata(
                id="prerequisite",
                description="Prerequisite agent",
                tools=[],
                memory_scope="shared",
                wait_for={"docs": [], "agents": []},
                parallel=False
            ), "Prerequisite prompt"),
            "dependent": (dependent_agent, "Dependent prompt")
        }
        
        template_dir = Path(__file__).parent.parent.parent / "scripts" / "templates"
        generator = Generator(template_dir)
        
        # Test app generation with dependencies
        app_code = generator.render_fastapi_app(agents)
        
        # Verify dependency chain is properly handled
        assert "prerequisite_node >> dependent_node" in app_code
        assert "pocketflow-communication pattern" in app_code
        assert "external control" in app_code


class TestValidationPatterns:
    """Test validation patterns from pocketflow-supervisor."""
    
    def test_output_validation_integration(self):
        """Test that generated agents include proper validation."""
        metadata = AgentMetadata(
            id="supervisor_agent",
            description="Agent with supervision",
            tools=[],
            memory_scope="shared",
            wait_for={"docs": [], "agents": []},
            parallel=False
        )
        
        template_dir = Path(__file__).parent.parent.parent / "scripts" / "templates"
        generator = Generator(template_dir)
        
        generated_code = generator.render_agent_node(metadata, "supervision test")
        
        # Verify supervisor validation patterns
        assert "yaml.safe_load" in generated_code
        assert "assert" in generated_code
        assert "structured_result is not None" in generated_code
        assert "result" in generated_code and "confidence" in generated_code


class TestPerformancePatterns:
    """Test performance optimization patterns."""
    
    def test_async_pattern_performance(self):
        """Test async patterns for performance optimization."""
        metadata = AgentMetadata(
            id="performance_agent",
            description="Performance test agent",
            tools=[],
            memory_scope="shared",
            wait_for={"docs": [], "agents": []},
            parallel=True
        )
        
        template_dir = Path(__file__).parent.parent.parent / "scripts" / "templates"
        generator = Generator(template_dir)
        
        generated_code = generator.render_agent_node(metadata, "performance test")
        
        # Verify async performance patterns
        assert "AsyncNode" in generated_code
        assert "async def exec_async" in generated_code
        assert "await call_llm_async" in generated_code
    
    def test_generation_speed(self):
        """Test that pattern generation completes in under 1 second."""
        import time
        
        metadata = AgentMetadata(
            id="speed_test",
            description="Speed test agent",
            tools=[],
            memory_scope="shared",
            wait_for={"docs": [], "agents": []},
            parallel=False
        )
        
        template_dir = Path(__file__).parent.parent.parent / "scripts" / "templates"
        generator = Generator(template_dir)
        
        start_time = time.perf_counter()
        generated_code = generator.render_agent_node(metadata, "speed test")
        end_time = time.perf_counter()
        
        generation_time = end_time - start_time
        
        # Verify sub-1s generation (generous margin for CI environments)
        assert generation_time < 1.0, f"Generation took {generation_time:.3f}s, exceeding 1s requirement"
        assert len(generated_code) > 100  # Ensure we actually generated something


class TestPatternCompliance:
    """Test overall pattern compliance and validation."""
    
    def test_cookbook_import_patterns(self):
        """Test that generated agents follow cookbook import patterns."""
        metadata = AgentMetadata(
            id="import_test",
            description="Import test agent",
            tools=[],
            memory_scope="shared",
            wait_for={"docs": [], "agents": []},
            parallel=False
        )
        
        template_dir = Path(__file__).parent.parent.parent / "scripts" / "templates"
        generator = Generator(template_dir)
        
        generated_code = generator.render_agent_node(metadata, "test")
        
        # Verify proper imports following cookbook patterns
        assert "from pocketflow import Node" in generated_code
        assert "import yaml" in generated_code
        assert "from utils import call_llm" in generated_code
    
    def test_bmad_to_pattern_mappings(self):
        """Test complete BMAD to PocketFlow pattern mappings."""
        # Test all major BMAD features
        metadata = AgentMetadata(
            id="complete_test",
            description="Complete pattern test agent",
            tools=["search", "calculator"],
            memory_scope="isolated",
            wait_for={"docs": [], "agents": ["preprocessor"]},
            parallel=True
        )
        
        template_dir = Path(__file__).parent.parent.parent / "scripts" / "templates"
        generator = Generator(template_dir)
        
        generated_code = generator.render_agent_node(metadata, "comprehensive test")
        
        # Verify all patterns are integrated
        assert "AsyncNode" in generated_code  # parallel=True
        assert "isolated" in generated_code   # memory_scope
        assert "preprocessor" in generated_code  # wait_for dependency
        assert "yaml.safe_load" in generated_code  # structured output
        assert "exec_fallback" in generated_code   # error handling
    
    def test_pattern_validation_rules(self):
        """Test that pattern validation rules are properly applied."""
        metadata = AgentMetadata(
            id="validation_test",
            description="Validation test agent",
            tools=[],
            memory_scope="shared",
            wait_for={"docs": [], "agents": []},
            parallel=False
        )
        
        template_dir = Path(__file__).parent.parent.parent / "scripts" / "templates"
        generator = Generator(template_dir)
        
        generated_code = generator.render_agent_node(metadata, "validation test")
        
        # Verify validation rules are present
        required_patterns = [
            "def prep(self, shared):",
            "def exec(self, prep_res):",  
            "def post(self, shared, prep_res, exec_res):",
            "def exec_fallback(self, prep_res, exc):",
            "assert structured_result is not None",
            "return exec_res.get(\"next_action\", \"default\")"
        ]
        
        for pattern in required_patterns:
            assert pattern in generated_code, f"Missing required pattern: {pattern}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])