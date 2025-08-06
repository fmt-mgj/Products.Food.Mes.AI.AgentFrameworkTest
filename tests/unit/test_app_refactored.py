"""Unit tests for refactored FastAPI application."""

import os
import time
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open
import pytest
from fastapi.testclient import TestClient
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
        mock_module.__dict__ = {"MockAgent": mock_agent_class, "other_attr": "value"}
        
        with patch("pathlib.Path.exists", return_value=True), \
             patch("pathlib.Path.glob") as mock_glob, \
             patch("importlib.import_module", return_value=mock_module), \
             patch("sys.path"), \
             patch("dir", return_value=["MockAgent", "other_attr"]):
            
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


class TestStartupProcess:
    """Test startup functionality."""
    
    def test_startup_timing(self):
        """Test startup timing measurement."""
        from generated.app import startup, state
        import asyncio
        
        # Reset state
        state.startup_duration = 0.0
        
        start_time = time.perf_counter()
        asyncio.run(startup())
        actual_duration = time.perf_counter() - start_time
        
        assert state.startup_duration > 0
        assert abs(state.startup_duration - actual_duration) < 0.1  # Within 100ms
        assert state.startup_time is not None


class TestEndpoints:
    """Test FastAPI endpoints."""
    
    def setup_method(self):
        """Set up test client."""
        # Import after potential patches
        from generated.app import app, state
        
        # Reset state
        state.agents = {}
        state.flows = {}
        state.config = {
            "server": {"host": "0.0.0.0", "port": 8000},
            "cors": {"origins": ["http://localhost:3000"]}
        }
        
        self.client = TestClient(app)
        self.state = state
    
    def test_health_endpoint(self):
        """Test health check endpoint."""
        # Set up state
        self.state.agents = {"test": MagicMock}
        self.state.startup_duration = 0.5
        
        response = self.client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["agents_loaded"] == 1
        assert data["startup_time"] == 0.5
        assert "timestamp" in data
        assert "version" in data
    
    def test_run_endpoint_no_flow(self):
        """Test /run endpoint with missing flow."""
        response = self.client.post("/run", json={
            "input": "test input",
            "flow": "nonexistent"
        })
        
        assert response.status_code == 422  # Validation error for invalid flow
    
    def test_run_endpoint_invalid_input(self):
        """Test /run endpoint with invalid input."""
        response = self.client.post("/run", json={
            "input": "",  # Empty input
            "flow": "default"
        })
        
        assert response.status_code == 422
        assert "Input cannot be empty" in str(response.json())
    
    def test_run_endpoint_success(self, mock_agent_class):
        """Test successful /run endpoint execution."""
        from generated.app import Flow
        
        # Set up flow with mock agent
        mock_flow = MagicMock(spec=Flow)
        mock_flow.run.return_value = "success"
        
        self.state.agents = {"test": mock_agent_class}
        self.state.flows = {"default": mock_flow}
        
        response = self.client.post("/run", json={
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
        
        # Verify flow.run was called with correct parameters
        mock_flow.run.assert_called_once()
        call_args = mock_flow.run.call_args[0][0]
        assert call_args["input"] == "test input"
        assert call_args["story_id"] == "S-123"
        assert call_args["flow"] == "default"
    
    def test_run_endpoint_flow_exception(self):
        """Test /run endpoint when flow execution fails."""
        from generated.app import Flow
        
        # Set up flow that raises exception
        mock_flow = MagicMock(spec=Flow)
        mock_flow.run.side_effect = Exception("Flow execution failed")
        
        self.state.flows = {"default": mock_flow}
        
        response = self.client.post("/run", json={
            "input": "test input",
            "flow": "default"
        })
        
        assert response.status_code == 500
        assert "Flow execution failed" in response.json()["detail"]
    
    def test_docs_endpoint(self):
        """Test that API docs are available."""
        response = self.client.get("/docs")
        assert response.status_code == 200
    
    def test_redoc_endpoint(self):
        """Test that ReDoc is available."""
        response = self.client.get("/redoc")
        assert response.status_code == 200


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


class TestIntegrationValidation:
    """Integration tests to validate the complete refactored application."""
    
    def test_complete_startup_sequence(self):
        """Test complete application startup with mocked components."""
        from generated.app import AppState, startup
        import asyncio
        
        # Create fresh state
        state = AppState()
        
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}), \
             patch("generated.app.load_dotenv"), \
             patch("pathlib.Path.exists", return_value=False):
            
            # Run startup
            asyncio.run(startup())
            
            # Verify configuration was loaded
            assert state.config["llm"]["api_key"] == "test-key"
            
            # Verify timing was recorded
            assert state.startup_duration >= 0
            assert state.startup_time is not None
    
    def test_cors_configuration(self):
        """Test CORS configuration is properly applied."""
        from generated.app import create_app, state
        
        # Set custom CORS origins
        state.config = {
            "cors": {"origins": ["https://example.com", "https://app.example.com"]}
        }
        
        app = create_app()
        
        # Check that CORS middleware is present
        cors_middleware = None
        for middleware in app.user_middleware:
            if hasattr(middleware, 'cls') and middleware.cls.__name__ == 'CORSMiddleware':
                cors_middleware = middleware
                break
        
        assert cors_middleware is not None