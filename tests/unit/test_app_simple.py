"""Simple unit tests for refactored app without TestClient dependency."""

import os
import time
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open
import pytest
from pydantic import ValidationError
from pocketflow import BaseNode


@pytest.fixture
def mock_agent_class():
    """Mock agent class that inherits from BaseNode."""
    class MockAgent(BaseNode):
        def __init__(self):
            super().__init__()
            self.retry_count = 3
        
        def prep(self, shared):
            return {"input": shared.get("input", "")}
        
        def exec(self, prep_result):
            return f"Processed: {prep_result['input']}"
        
        def post(self, shared, prep_result, exec_result):
            shared["test_result"] = exec_result
            return "success"
    
    return MockAgent


class TestAppState:
    """Test AppState class functionality."""
    
    def test_init(self):
        """Test AppState initialization."""
        from generated.app import AppState
        state = AppState()
        
        assert isinstance(state.config, dict)
        assert isinstance(state.agents, dict)
        assert isinstance(state.flows, dict)
        assert state.startup_time is None
        assert state.startup_duration == 0.0
    
    def test_load_config_with_defaults(self):
        """Test configuration loading with defaults."""
        from generated.app import AppState
        
        with patch("generated.app.load_dotenv"), \
             patch.dict(os.environ, {}, clear=True):
            
            state = AppState()
            state.load_config()
            
            assert state.config["server"]["host"] == "0.0.0.0"
            assert state.config["server"]["port"] == 8000
            assert state.config["llm"]["provider"] == "openai"
            assert state.config["cors"]["origins"] == ["http://localhost:3000"]
    
    def test_load_config_with_env_vars(self):
        """Test configuration loading with environment variables."""
        from generated.app import AppState
        
        env_vars = {
            "SERVER_HOST": "127.0.0.1",
            "SERVER_PORT": "9000",
            "OPENAI_API_KEY": "test-key",
            "CORS_ORIGINS": "http://localhost:3000,https://app.example.com"
        }
        
        with patch("generated.app.load_dotenv"), \
             patch.dict(os.environ, env_vars):
            
            state = AppState()
            state.load_config()
            
            assert state.config["server"]["host"] == "127.0.0.1"
            assert state.config["server"]["port"] == 9000
            assert state.config["llm"]["api_key"] == "test-key"
            assert len(state.config["cors"]["origins"]) == 2
            assert "https://app.example.com" in state.config["cors"]["origins"]
    
    def test_load_agents_no_directory(self):
        """Test agent loading when directory doesn't exist."""
        from generated.app import AppState
        
        with patch("pathlib.Path.exists", return_value=False):
            state = AppState()
            state.load_agents()
            
            assert len(state.agents) == 0
    
    def test_load_agents_success(self, mock_agent_class):
        """Test successful agent loading."""
        from generated.app import AppState
        
        mock_module = MagicMock()
        # Properly mock the module attributes
        setattr(mock_module, "MockAgent", mock_agent_class)
        setattr(mock_module, "other_attr", "value")
        
        with patch("pathlib.Path.exists", return_value=True), \
             patch("pathlib.Path.glob") as mock_glob, \
             patch("importlib.import_module", return_value=mock_module), \
             patch("sys.path"):
            
            mock_file = MagicMock()
            mock_file.name = "test.py"
            mock_file.stem = "test"
            mock_glob.return_value = [mock_file]
            
            state = AppState()
            state.load_agents()
            
            assert "test" in state.agents
            assert state.agents["test"] == mock_agent_class
    
    def test_create_flows_no_agents(self):
        """Test flow creation with no agents."""
        from generated.app import AppState
        
        state = AppState()
        state.create_flows()
        
        assert "default" in state.flows
        assert state.flows["default"] is not None
    
    def test_create_flows_with_agents(self, mock_agent_class):
        """Test flow creation with agents."""
        from generated.app import AppState
        
        state = AppState()
        state.agents["test"] = mock_agent_class
        state.create_flows()
        
        assert "default" in state.flows
        assert state.flows["default"] is not None


class TestRequestValidation:
    """Test request model validation."""
    
    def test_run_request_valid(self):
        """Test valid RunRequest."""
        from generated.app import RunRequest
        
        request = RunRequest(input="test input", flow="default", story_id="S-123")
        assert request.input == "test input"
        assert request.flow == "default"
        assert request.story_id == "S-123"
    
    def test_run_request_empty_input(self):
        """Test RunRequest with empty input."""
        from generated.app import RunRequest
        
        with pytest.raises(ValidationError) as exc_info:
            RunRequest(input="", flow="default")
        
        assert "Input cannot be empty" in str(exc_info.value)
    
    def test_run_request_long_input(self):
        """Test RunRequest with too long input."""
        from generated.app import RunRequest
        
        long_input = "x" * 10001
        with pytest.raises(ValidationError) as exc_info:
            RunRequest(input=long_input, flow="default")
        
        assert "Input too long" in str(exc_info.value)
    
    def test_run_request_invalid_flow(self):
        """Test RunRequest with invalid flow."""
        from generated.app import RunRequest
        
        with pytest.raises(ValidationError) as exc_info:
            RunRequest(input="test", flow="invalid")
        
        assert "Flow must be one of" in str(exc_info.value)


class TestEndpointLogic:
    """Test endpoint logic without HTTP client."""
    
    def test_health_check_function(self):
        """Test health_check function directly."""
        from generated.app import health_check, state
        import asyncio
        
        # Set up state
        state.agents = {"test": MagicMock}
        state.startup_duration = 0.5
        
        response = asyncio.run(health_check())
        
        assert response.status == "healthy"
        assert response.agents_loaded == 1
        assert response.startup_time == 0.5
        assert response.version is not None
        assert response.timestamp is not None
    
    def test_run_flow_function_missing_flow(self, mock_agent_class):
        """Test run_flow function with missing flow."""
        from generated.app import run_flow, RunRequest, state
        from fastapi import HTTPException
        import asyncio
        
        # Clear flows but keep default as valid
        state.flows = {"other": MagicMock()}
        
        request = RunRequest(input="test", flow="default")
        
        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(run_flow(request))
        
        assert exc_info.value.status_code == 404
        assert "not found" in exc_info.value.detail
    
    def test_run_flow_function_success(self, mock_agent_class):
        """Test run_flow function success case."""
        from generated.app import run_flow, RunRequest, state, Flow
        import asyncio
        
        # Set up mock flow
        mock_flow = MagicMock(spec=Flow)
        mock_flow.run.return_value = "success"
        
        state.agents = {"test": mock_agent_class}
        state.flows = {"default": mock_flow}
        
        request = RunRequest(input="test input", flow="default", story_id="S-123")
        
        response = asyncio.run(run_flow(request))
        
        assert response.result is not None
        assert isinstance(response.agent_results, dict)
        assert response.execution_time >= 0
        
        # Verify flow.run was called
        mock_flow.run.assert_called_once()
        call_args = mock_flow.run.call_args[0][0]
        assert call_args["input"] == "test input"
        assert call_args["story_id"] == "S-123"
        assert call_args["flow"] == "default"
    
    def test_run_flow_function_exception(self):
        """Test run_flow function when flow raises exception."""
        from generated.app import run_flow, RunRequest, state, Flow
        from fastapi import HTTPException
        import asyncio
        
        # Set up mock flow that raises exception
        mock_flow = MagicMock(spec=Flow)
        mock_flow.run.side_effect = Exception("Test error")
        
        state.flows = {"default": mock_flow}
        
        request = RunRequest(input="test", flow="default")
        
        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(run_flow(request))
        
        assert exc_info.value.status_code == 500
        assert "Test error" in exc_info.value.detail


class TestStartupProcess:
    """Test startup functionality."""
    
    def test_startup_timing(self):
        """Test startup timing measurement."""
        from generated.app import startup, state
        import asyncio
        
        # Reset state
        original_duration = state.startup_duration
        state.startup_duration = 0.0
        
        # Set up minimal config to avoid KeyError
        state.config = {"cors": {"origins": ["http://localhost:3000"]}}
        
        with patch.object(state, 'load_config'), \
             patch.object(state, 'load_agents'), \
             patch.object(state, 'create_flows'):
            
            start_time = time.perf_counter()
            asyncio.run(startup())
            actual_duration = time.perf_counter() - start_time
            
            assert state.startup_duration > 0
            assert abs(state.startup_duration - actual_duration) < 0.1  # Within 100ms
            assert state.startup_time is not None
        
        # Restore original duration
        state.startup_duration = original_duration


class TestVersionLoading:
    """Test VERSION file loading."""
    
    def test_version_loading_success(self):
        """Test successful VERSION file loading."""
        with patch("builtins.open", mock_open(read_data="1.2.3\n")):
            import importlib
            import generated.app
            importlib.reload(generated.app)
            
            assert generated.app.VERSION == "1.2.3"
    
    def test_version_loading_fallback(self):
        """Test VERSION file loading with fallback."""
        with patch("builtins.open", side_effect=FileNotFoundError):
            import importlib
            import generated.app
            importlib.reload(generated.app)
            
            assert generated.app.VERSION == "0.31"


class TestCompleteIntegration:
    """Integration tests for complete application functionality."""
    
    def test_app_creation(self):
        """Test FastAPI app can be created."""
        from generated.app import create_app, state
        
        # Set up basic config
        state.config = {
            "cors": {"origins": ["http://localhost:3000"]}
        }
        
        app = create_app()
        
        assert app is not None
        assert app.title == "BMAD PocketFlow Runtime"
        assert app.docs_url == "/docs"
        assert app.redoc_url == "/redoc"
    
    def test_cors_configuration(self):
        """Test CORS configuration."""
        from generated.app import create_app, state
        
        # Set custom CORS origins
        state.config = {
            "cors": {"origins": ["https://example.com", "https://app.example.com"]}
        }
        
        app = create_app()
        
        # Verify app was created (detailed CORS testing requires more complex setup)
        assert app is not None
    
    def test_full_state_lifecycle(self, mock_agent_class):
        """Test complete state lifecycle."""
        from generated.app import AppState
        
        state = AppState()
        
        # Test configuration
        with patch("generated.app.load_dotenv"), \
             patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            
            state.load_config()
            assert state.config["llm"]["api_key"] == "test-key"
        
        # Test agent loading
        mock_module = MagicMock()
        setattr(mock_module, "TestAgent", mock_agent_class)
        
        with patch("pathlib.Path.exists", return_value=True), \
             patch("pathlib.Path.glob") as mock_glob, \
             patch("importlib.import_module", return_value=mock_module), \
             patch("sys.path"):
            
            mock_file = MagicMock()
            mock_file.name = "test.py"
            mock_file.stem = "test"
            mock_glob.return_value = [mock_file]
            
            state.load_agents()
            assert "test" in state.agents
        
        # Test flow creation
        state.create_flows()
        assert "default" in state.flows
        
        # Test flow execution
        flow = state.flows["default"]
        shared = {"input": "test"}
        result = flow.run(shared)
        
        # Should complete without error
        assert result is not None