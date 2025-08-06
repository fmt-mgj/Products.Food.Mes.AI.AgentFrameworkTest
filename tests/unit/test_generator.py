"""Unit tests for BMAD to PocketFlow code generator."""

import ast
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from scripts.generator import Generator, GenerationError, generate_from_config
from scripts.parser import AgentMetadata


@pytest.fixture
def template_dir():
    """Fixture providing path to test templates."""
    return Path(__file__).parent.parent.parent / "scripts" / "templates"


@pytest.fixture
def temp_output_dir():
    """Fixture providing temporary directory for test outputs."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_agent_metadata():
    """Fixture providing sample agent metadata."""
    return AgentMetadata(
        id="test_agent",
        description="A test agent for unit testing",
        tools=["web_search"],
        memory_scope="isolated",
        wait_for={"docs": [], "agents": []},
        parallel=False
    )


@pytest.fixture
def sample_agents_dict(sample_agent_metadata):
    """Fixture providing sample agents dictionary."""
    return {
        "test_agent": (
            sample_agent_metadata,
            "You are a helpful assistant. Please analyze the input and provide insights."
        )
    }


class TestGenerator:
    """Test cases for Generator class."""

    def test_generator_init_valid_template_dir(self, template_dir):
        """Test generator initialization with valid template directory."""
        generator = Generator(template_dir)
        assert generator.template_dir == template_dir
        assert generator.env is not None

    def test_generator_init_invalid_template_dir(self):
        """Test generator initialization with invalid template directory."""
        with pytest.raises(GenerationError, match="Template directory does not exist"):
            Generator(Path("nonexistent"))

    def test_render_agent_node(self, template_dir, sample_agent_metadata):
        """Test rendering a single agent node."""
        generator = Generator(template_dir)
        prompt_content = "You are a test agent."
        
        result = generator.render_agent_node(sample_agent_metadata, prompt_content)
        
        assert isinstance(result, str)
        assert "TestAgentNode" in result
        assert "Node" in result
        assert prompt_content in result
        assert "call_llm" in result
        
        # Validate generated code syntax
        ast.parse(result)

    def test_render_fastapi_app(self, template_dir, sample_agents_dict):
        """Test rendering FastAPI application."""
        generator = Generator(template_dir)
        
        result = generator.render_fastapi_app(sample_agents_dict)
        
        assert isinstance(result, str)
        assert "FastAPI" in result
        assert "TestAgentNode" in result
        assert "/health" in result
        assert "/run" in result
        
        # Validate generated code syntax
        ast.parse(result)

    def test_render_utils(self, template_dir):
        """Test rendering utils module."""
        generator = Generator(template_dir)
        
        result = generator.render_utils()
        
        assert isinstance(result, str)
        assert "call_llm" in result
        assert "OpenAI" in result
        
        # Validate generated code syntax
        ast.parse(result)

    def test_render_agents_init(self, template_dir, sample_agents_dict):
        """Test rendering agents __init__.py file."""
        generator = Generator(template_dir)
        
        result = generator.render_agents_init(sample_agents_dict)
        
        assert isinstance(result, str)
        assert "TestAgentNode" in result
        assert "__all__" in result
        
        # Validate generated code syntax
        ast.parse(result)

    def test_generate_all_creates_files(self, template_dir, sample_agents_dict, temp_output_dir):
        """Test that generate_all creates all expected files."""
        generator = Generator(template_dir)
        
        with patch.object(generator, 'format_code', return_value=[]):
            generated_files = generator.generate_all(sample_agents_dict, temp_output_dir)
        
        # Check that files were created
        expected_files = [
            temp_output_dir / "agents" / "test_agent.py",
            temp_output_dir / "app.py", 
            temp_output_dir / "utils.py",
            temp_output_dir / "agents" / "__init__.py"
        ]
        
        for file_path in expected_files:
            assert file_path.exists()
            assert str(file_path) in generated_files
        
        # Check file contents
        agent_file = temp_output_dir / "agents" / "test_agent.py"
        agent_content = agent_file.read_text()
        assert "TestAgentNode" in agent_content
        ast.parse(agent_content)  # Validate syntax

    def test_generate_all_no_agents(self, template_dir, temp_output_dir):
        """Test generate_all with empty agents dictionary."""
        generator = Generator(template_dir)
        
        with patch.object(generator, 'format_code', return_value=[]):
            generated_files = generator.generate_all({}, temp_output_dir)
        
        # Should still create app.py, utils.py and agents/__init__.py
        assert len(generated_files) == 3
        
        app_file = temp_output_dir / "app.py"
        assert app_file.exists()
        app_content = app_file.read_text()
        ast.parse(app_content)  # Validate syntax

    @patch('subprocess.run')
    def test_format_code_success(self, mock_run, template_dir):
        """Test successful code formatting."""
        mock_run.return_value.returncode = 0
        mock_run.return_value.stderr = ""
        mock_run.return_value.stdout = ""
        
        generator = Generator(template_dir)
        test_files = [Path("test.py")]
        
        issues = generator.format_code(test_files)
        
        assert issues == []
        assert mock_run.call_count == 2  # black and ruff

    @patch('subprocess.run')
    def test_format_code_black_failure(self, mock_run, template_dir):
        """Test code formatting with black failure."""
        mock_run.side_effect = [
            # Black fails
            type('Result', (), {'returncode': 1, 'stderr': 'Black error', 'stdout': ''})(),
            # Ruff succeeds  
            type('Result', (), {'returncode': 0, 'stderr': '', 'stdout': ''})()
        ]
        
        generator = Generator(template_dir)
        test_files = [Path("test.py")]
        
        issues = generator.format_code(test_files)
        
        assert len(issues) == 1
        assert "Black formatting failed" in issues[0]

    def test_format_code_empty_files(self, template_dir):
        """Test formatting with empty file list."""
        generator = Generator(template_dir)
        
        issues = generator.format_code([])
        
        assert issues == []


class TestGenerateFromConfig:
    """Test cases for generate_from_config function."""

    def test_generate_from_config(self, template_dir, sample_agents_dict, temp_output_dir):
        """Test high-level generate_from_config function."""
        config = {"agents": sample_agents_dict}
        
        with patch('scripts.generator.Generator.format_code', return_value=[]):
            generated_files = generate_from_config(config, temp_output_dir, template_dir)
        
        assert len(generated_files) == 4
        
        # Verify app.py was created
        app_file = temp_output_dir / "app.py"
        assert app_file.exists()
        assert str(app_file) in generated_files

    def test_generate_from_config_no_agents(self, template_dir, temp_output_dir):
        """Test generate_from_config with no agents."""
        config = {"agents": {}}
        
        with patch('scripts.generator.Generator.format_code', return_value=[]):
            generated_files = generate_from_config(config, temp_output_dir, template_dir)
        
        assert len(generated_files) == 3  # app.py, utils.py, agents/__init__.py


class TestPerformance:
    """Test cases for performance requirements."""

    def test_generation_speed(self, template_dir, temp_output_dir):
        """Test that generation completes within 500ms for typical project."""
        import time
        
        # Create test agents (simulate typical project)
        agents = {}
        for i in range(5):  # 5 agents
            agent_id = f"agent_{i}"
            metadata = AgentMetadata(
                id=agent_id,
                description=f"Agent {i}",
                tools=[],
                memory_scope="isolated"
            )
            prompt = f"You are agent {i}. Process the input accordingly."
            agents[agent_id] = (metadata, prompt)
        
        generator = Generator(template_dir)
        
        start_time = time.time()
        
        with patch.object(generator, 'format_code', return_value=[]):
            generated_files = generator.generate_all(agents, temp_output_dir)
        
        generation_time = time.time() - start_time
        
        assert generation_time < 0.5  # Must complete in under 500ms
        assert len(generated_files) == 3 + len(agents)  # app, utils, agents/__init__ + agent files


class TestCodeQuality:
    """Test cases for generated code quality."""

    def test_generated_code_syntax(self, template_dir, sample_agents_dict, temp_output_dir):
        """Test that all generated code has valid Python syntax."""
        generator = Generator(template_dir)
        
        with patch.object(generator, 'format_code', return_value=[]):
            generated_files = generator.generate_all(sample_agents_dict, temp_output_dir)
        
        for file_path, content in generated_files.items():
            if file_path.endswith('.py'):
                # Should not raise SyntaxError
                ast.parse(content)

    def test_generated_imports(self, template_dir, sample_agents_dict, temp_output_dir):
        """Test that generated code has correct imports."""
        generator = Generator(template_dir)
        
        with patch.object(generator, 'format_code', return_value=[]):
            generated_files = generator.generate_all(sample_agents_dict, temp_output_dir)
        
        # Check agent file imports
        agent_file = str(temp_output_dir / "agents" / "test_agent.py")
        agent_content = generated_files[agent_file]
        assert "from pocketflow import Node" in agent_content
        assert "from utils import call_llm" in agent_content
        
        # Check app file imports
        app_file = str(temp_output_dir / "app.py")
        app_content = generated_files[app_file]
        assert "from fastapi import FastAPI" in app_content
        assert "from pocketflow import Flow" in app_content