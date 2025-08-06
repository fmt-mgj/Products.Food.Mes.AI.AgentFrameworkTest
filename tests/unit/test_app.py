"""Unit tests for FastAPI application."""

import os
import time
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open
import pytest
from fastapi.testclient import TestClient
import yaml


@pytest.fixture
def mock_config():
    """Mock configuration data."""
    return {
        "llm": {"provider": "openai", "model": "gpt-4"},
        "memory": {"backend": "file", "file_path": "./memory"},
        "logging": {"level": "INFO"},
        "server": {"host": "0.0.0.0", "port": 8000}
    }


@pytest.fixture
def mock_version():
    """Mock VERSION file content."""
    return "0.31"


class TestConfigurationLoading:
    """Test configuration loading functionality."""
    
    def test_load_config_with_runtime_yaml(self, mock_config):
        """Test loading configuration from runtime.yaml."""
        with patch("pathlib.Path.exists") as mock_exists, \
             patch("builtins.open", mock_open(read_data=yaml.dump(mock_config))) as mock_file, \
             patch("generated.app.load_dotenv") as mock_dotenv, \
             patch.dict(os.environ, {}, clear=True):
            
            mock_exists.return_value = True
            
            # Import after patching
            from generated.app import load_config
            
            result = load_config()
            
            assert result == mock_config
            mock_dotenv.assert_called_once()
    
    def test_load_config_without_runtime_yaml(self):
        """Test loading configuration when runtime.yaml doesn't exist."""
        with patch("pathlib.Path.exists") as mock_exists, \
             patch("generated.app.load_dotenv") as mock_dotenv:
            
            mock_exists.return_value = False
            
            from generated.app import load_config
            
            result = load_config()
            
            # Should return defaults
            assert "llm" in result
            assert "memory" in result
            assert result["llm"]["provider"] == "openai"
    
    def test_load_config_with_environment_variables(self, mock_config):
        """Test that environment variables override config file."""
        with patch("pathlib.Path.exists") as mock_exists, \
             patch("builtins.open", mock_open(read_data=yaml.dump(mock_config))), \
             patch("generated.app.load_dotenv"), \
             patch.dict(os.environ, {"OPENAI_API_KEY": "test-key", "ANTHROPIC_API_KEY": "test-key-2"}):
            
            mock_exists.return_value = True
            
            from generated.app import load_config
            
            result = load_config()
            
            assert result["llm"]["api_key"] == "test-key"
            assert result["anthropic"]["api_key"] == "test-key-2"


class TestDynamicAgentImport:
    """Test dynamic agent import functionality."""
    
    def test_load_agents_success(self):
        """Test successful agent loading."""
        mock_node_class = MagicMock()
        mock_module = MagicMock()
        mock_module.AnalystNode = mock_node_class
        
        with patch("pathlib.Path.exists") as mock_exists, \
             patch("pathlib.Path.glob") as mock_glob, \
             patch("importlib.import_module") as mock_import, \
             patch("sys.path"):
            
            mock_exists.return_value = True
            mock_file = MagicMock()
            mock_file.name = "analyst.py"
            mock_file.stem = "analyst"
            mock_glob.return_value = [mock_file]
            mock_import.return_value = mock_module
            
            from generated.app import load_agents
            
            result = load_agents()
            
            assert "analyst" in result
            assert result["analyst"] == mock_node_class
    
    def test_load_agents_no_directory(self):
        """Test agent loading when agents directory doesn't exist."""
        with patch("pathlib.Path.exists") as mock_exists:
            mock_exists.return_value = False
            
            from generated.app import load_agents
            
            result = load_agents()
            
            assert result == {}
    
    def test_load_agents_import_error(self):
        """Test agent loading with import error."""
        with patch("pathlib.Path.exists") as mock_exists, \
             patch("pathlib.Path.glob") as mock_glob, \
             patch("importlib.import_module") as mock_import, \
             patch("sys.path"):
            
            mock_exists.return_value = True
            mock_file = MagicMock()
            mock_file.name = "broken.py"
            mock_file.stem = "broken"
            mock_glob.return_value = [mock_file]
            mock_import.side_effect = ImportError("Module not found")
            
            from generated.app import load_agents
            
            result = load_agents()
            
            assert result == {}


class TestFastAPIEndpoints:
    """Test FastAPI endpoints."""
    
    def test_health_endpoint(self, mock_version):
        """Test health check endpoint."""
        with patch("builtins.open", mock_open(read_data=mock_version)), \
             patch("generated.app.config", {"test": True}), \
             patch("generated.app.agent_registry", {"agent1": MagicMock()}), \
             patch("generated.app.startup_duration", 0.5):
            
            # Import and create client after patching
            from generated.app import app
            client = TestClient(app)
            response = client.get("/health")
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            assert data["version"] == mock_version
            assert data["agents_loaded"] == 1
            assert data["config_loaded"] is True
            assert data["startup_time"] == 0.5
    
    def test_run_endpoint_no_agents(self):
        """Test run endpoint with no agents loaded."""
        with patch("builtins.open", mock_open(read_data="0.31")), \
             patch("generated.app.agent_registry", {}):
            
            from generated.app import app
            client = TestClient(app)
            response = client.post("/run", json={"input": "test"})
            
            assert response.status_code == 503
            assert "No agents loaded" in response.json()["detail"]
    
    def test_run_endpoint_success(self):
        """Test successful run endpoint execution."""
        mock_node = MagicMock()
        mock_flow = MagicMock()
        mock_flow.run.return_value = "success"
        
        with patch("builtins.open", mock_open(read_data="0.31")), \
             patch("generated.app.agent_registry", {"test": MagicMock}), \
             patch("generated.app.Flow") as mock_flow_class:
            
            mock_flow_class.return_value = mock_flow
            
            from generated.app import app
            client = TestClient(app)
            response = client.post("/run", json={
                "input": "test input",
                "flow": "default",
                "story_id": "S-123"
            })
            
            assert response.status_code == 200
            data = response.json()
            assert "result" in data
            assert "agent_results" in data
            assert "execution_time" in data
            assert data["execution_time"] >= 0


class TestStartupTiming:
    """Test startup timing requirements."""
    
    def test_startup_time_measurement(self):
        """Test that startup time is properly measured."""
        with patch("generated.app.load_config") as mock_load_config, \
             patch("generated.app.load_agents") as mock_load_agents, \
             patch("time.perf_counter") as mock_perf_counter:
            
            # Mock timing
            mock_perf_counter.side_effect = [0.0, 0.8]  # Start and end times
            mock_load_config.return_value = {}
            mock_load_agents.return_value = {}
            
            from generated.app import startup_event
            
            # Run startup event
            import asyncio
            asyncio.run(startup_event())
            
            from generated.app import startup_duration
            
            assert startup_duration == 0.8
    
    def test_startup_warning_for_slow_startup(self):
        """Test warning is logged for slow startup."""
        with patch("generated.app.load_config") as mock_load_config, \
             patch("generated.app.load_agents") as mock_load_agents, \
             patch("time.perf_counter") as mock_perf_counter, \
             patch("generated.app.logger") as mock_logger:
            
            # Mock slow startup
            mock_perf_counter.side_effect = [0.0, 1.5]  # Start and end times
            mock_load_config.return_value = {}
            mock_load_agents.return_value = {}
            
            from generated.app import startup_event
            
            # Run startup event
            import asyncio
            asyncio.run(startup_event())
            
            # Check warning was logged
            mock_logger.warning.assert_called()
            warning_call = mock_logger.warning.call_args[0][0]
            assert "Startup exceeded 1 second" in warning_call


class TestVersionLoading:
    """Test VERSION file loading."""
    
    def test_version_loading_success(self):
        """Test successful VERSION file loading."""
        with patch("builtins.open", mock_open(read_data="1.0.0\n")):
            # Reload the module to test VERSION loading
            import importlib
            import generated.app
            importlib.reload(generated.app)
            
            assert generated.app.VERSION == "1.0.0"
    
    def test_version_loading_fallback(self):
        """Test VERSION file loading with fallback."""
        with patch("builtins.open", side_effect=FileNotFoundError):
            import importlib
            import generated.app
            importlib.reload(generated.app)
            
            assert generated.app.VERSION == "0.31"


class TestIntegration:
    """Integration tests for full application."""
    
    def test_full_application_startup(self):
        """Test complete application startup sequence."""
        mock_config = {
            "llm": {"provider": "openai"},
            "logging": {"level": "INFO"}
        }
        
        with patch("pathlib.Path.exists") as mock_exists, \
             patch("builtins.open", mock_open(read_data=yaml.dump(mock_config))), \
             patch("generated.app.load_dotenv"), \
             patch("sys.path"), \
             patch.dict(os.environ, {}, clear=True):
            
            mock_exists.return_value = True
            
            # Import modules to reset state
            import generated.app
            import importlib
            importlib.reload(generated.app)
            
            from generated.app import startup_event
            
            # Run startup
            import asyncio
            asyncio.run(startup_event())
            
            # Verify state after startup
            from generated.app import config, agent_registry, startup_duration
            assert config is not None
            assert isinstance(agent_registry, dict)
            assert startup_duration is not None
            assert startup_duration >= 0