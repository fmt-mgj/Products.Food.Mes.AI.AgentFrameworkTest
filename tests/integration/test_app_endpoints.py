"""Integration tests for FastAPI app endpoints."""

import json
import os
import tempfile
import time
from pathlib import Path
import pytest
import yaml


@pytest.fixture(scope="module")
def test_config_files():
    """Create temporary config files for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        config_dir = Path(temp_dir) / "config"
        config_dir.mkdir()
        
        # Create runtime.yaml
        runtime_config = {
            "llm": {"provider": "openai", "model": "gpt-4"},
            "memory": {"backend": "file", "file_path": "./memory"},
            "logging": {"level": "INFO"},
            "server": {"host": "0.0.0.0", "port": 8001}  # Different port for testing
        }
        
        with open(config_dir / "runtime.yaml", "w") as f:
            yaml.dump(runtime_config, f)
        
        # Create secrets.env
        with open(config_dir / "secrets.env", "w") as f:
            f.write("OPENAI_API_KEY=test-key\n")
        
        # Create VERSION file
        with open(Path(temp_dir) / "VERSION", "w") as f:
            f.write("0.31\n")
        
        yield temp_dir


class TestAppStartup:
    """Test application startup functionality."""
    
    def test_app_imports_successfully(self):
        """Test that the app module can be imported without errors."""
        try:
            import generated.app
            assert generated.app.app is not None
            assert generated.app.VERSION is not None
        except ImportError as e:
            pytest.fail(f"Failed to import app module: {e}")
    
    def test_startup_timing_simulation(self):
        """Test startup timing measurement in isolation."""
        from generated.app import startup_event
        import asyncio
        
        start_time = time.perf_counter()
        asyncio.run(startup_event())
        duration = time.perf_counter() - start_time
        
        # Verify startup completed
        from generated.app import startup_duration
        assert startup_duration is not None
        assert startup_duration > 0
        assert duration < 2.0  # Should be very fast in test environment


class TestHealthEndpoint:
    """Test health endpoint functionality."""
    
    def test_health_endpoint_structure(self):
        """Test health endpoint returns proper structure."""
        from generated.app import health_check
        import asyncio
        
        # Mock the global state
        import generated.app
        generated.app.agent_registry = {"test": object()}
        generated.app.config = {"test": True}
        generated.app.startup_duration = 0.5
        
        response = asyncio.run(health_check())
        
        assert hasattr(response, 'status')
        assert hasattr(response, 'version')
        assert hasattr(response, 'agents_loaded')
        assert hasattr(response, 'config_loaded')
        assert hasattr(response, 'timestamp')
        assert hasattr(response, 'startup_time')
        
        assert response.status == "healthy"
        assert response.agents_loaded == 1
        assert response.config_loaded is True
        assert response.startup_time == 0.5


class TestConfigurationValidation:
    """Test configuration loading validation."""
    
    def test_config_loader_with_mock_files(self):
        """Test configuration loading with mocked file system."""
        from unittest.mock import patch, mock_open
        from generated.app import load_config
        
        mock_config = {
            "llm": {"provider": "openai", "model": "gpt-4"},
            "memory": {"backend": "file"},
            "server": {"port": 8000}
        }
        
        with patch("pathlib.Path.exists", return_value=True), \
             patch("builtins.open", mock_open(read_data=yaml.dump(mock_config))), \
             patch("generated.app.load_dotenv"), \
             patch.dict(os.environ, {}, clear=True):
            
            result = load_config()
            
            assert result["llm"]["provider"] == "openai"
            assert result["memory"]["backend"] == "file"
            assert result["server"]["port"] == 8000
    
    def test_agent_loading_with_mock_modules(self):
        """Test agent loading with mocked modules."""
        from unittest.mock import patch, MagicMock
        from generated.app import load_agents
        
        mock_node = MagicMock()
        mock_module = MagicMock()
        mock_module.TestNode = mock_node
        
        with patch("pathlib.Path.exists", return_value=True), \
             patch("pathlib.Path.glob") as mock_glob, \
             patch("importlib.import_module", return_value=mock_module), \
             patch("sys.path"):
            
            # Mock a python file
            mock_file = MagicMock()
            mock_file.name = "test.py"
            mock_file.stem = "test"
            mock_glob.return_value = [mock_file]
            
            result = load_agents()
            
            assert "test" in result
            assert result["test"] == mock_node


class TestApplicationIntegration:
    """Integration tests for the complete application."""
    
    def test_version_loading_integration(self):
        """Test VERSION file loading integration."""
        # Test with existing VERSION file
        try:
            with open("VERSION", "r") as f:
                version = f.read().strip()
            
            # Reload app to test version loading
            import importlib
            import generated.app
            importlib.reload(generated.app)
            
            assert generated.app.VERSION == version
        except FileNotFoundError:
            # If no VERSION file exists, should use default
            import importlib
            import generated.app
            importlib.reload(generated.app)
            
            assert generated.app.VERSION == "0.31"
    
    def test_configuration_environment_override(self):
        """Test that environment variables properly override config."""
        from unittest.mock import patch, mock_open
        from generated.app import load_config
        
        base_config = {"llm": {"provider": "openai"}}
        
        with patch("pathlib.Path.exists", return_value=True), \
             patch("builtins.open", mock_open(read_data=yaml.dump(base_config))), \
             patch("generated.app.load_dotenv"), \
             patch.dict(os.environ, {"OPENAI_API_KEY": "test-env-key"}):
            
            result = load_config()
            
            assert result["llm"]["api_key"] == "test-env-key"
    
    def test_missing_config_fallback(self):
        """Test fallback behavior when config files are missing."""
        from unittest.mock import patch
        from generated.app import load_config
        
        with patch("pathlib.Path.exists", return_value=False), \
             patch("generated.app.load_dotenv"):
            
            result = load_config()
            
            # Should return default configuration
            assert "llm" in result
            assert "memory" in result
            assert "server" in result
            assert result["llm"]["provider"] == "openai"