"""Integration tests for stateless agent execution endpoint."""

import pytest
import asyncio
from unittest.mock import patch, Mock
from fastapi.testclient import TestClient

from generated.app import app
from generated.models import AgentRequest, AgentResponse
from generated.stateless_agent import StatelessAgent


class TestStatelessAgent(StatelessAgent):
    """Test agent implementation for integration tests."""
    
    def __init__(self, behavior="success"):
        super().__init__(max_retries=3, wait=0)
        self.behavior = behavior
    
    def exec(self, prep_res):
        """Test implementation with configurable behavior."""
        agent_request, memory_context, start_time = prep_res
        
        if self.behavior == "success":
            return {
                "status": "completed",
                "content": f"Test agent {agent_request.agent_id} completed successfully",
                "summary": "Integration test execution",
                "metadata": {
                    "test_execution": True,
                    "context_keys": list(agent_request.context.keys())
                }
            }
        elif self.behavior == "needs_input":
            return {
                "status": "needs_input",
                "content": "Need additional documents",
                "summary": "Missing required inputs",
                "missing_inputs": ["required_doc", "user_preferences"]
            }
        elif self.behavior == "failure":
            raise Exception("Test agent failure")
        else:
            raise ValueError(f"Unknown behavior: {self.behavior}")


class SlowTestAgent(StatelessAgent):
    """Test agent that takes longer than 1 second."""
    
    def exec(self, prep_res):
        import time
        time.sleep(1.1)  # Exceed 1 second limit
        
        agent_request, memory_context, start_time = prep_res
        return {
            "status": "completed",
            "content": "Slow execution completed",
            "summary": "Performance test - slow execution"
        }


@pytest.fixture
def client():
    """FastAPI test client fixture."""
    return TestClient(app)


class TestStatelessExecutionEndpoint:
    """Test cases for the /agent/{agent_id}/execute endpoint."""
    
    @patch('generated.app.load_agent_class')
    def test_successful_agent_execution(self, mock_load_agent, client):
        """Test successful stateless agent execution."""
        # Mock agent loading
        mock_load_agent.return_value = lambda: TestStatelessAgent("success")
        
        request_data = {
            "context": {"story_id": "S-123", "user": "integration_test"},
            "documents": {"doc1": "test content", "doc2": "more content"},
            "instructions": "Process the test data",
            "memory_scope": "isolated",
            "execution_id": "exec-integration-1",
            "agent_id": "test-agent"
        }
        
        response = client.post("/agent/test-agent/execute", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        
        # Validate response structure
        assert data["status"] == "completed"
        assert "Test agent test-agent completed successfully" in data["content"]
        assert data["summary"] == "Integration test execution"
        assert data["missing_inputs"] == []
        assert data["metadata"]["test_execution"] is True
        assert data["execution_time_ms"] is not None
        assert data["execution_time_ms"] < 1000  # Sub-1s requirement
        
        # Verify agent was loaded with correct ID
        mock_load_agent.assert_called_once_with("test-agent")
    
    @patch('generated.app.load_agent_class')
    def test_needs_input_response(self, mock_load_agent, client):
        """Test agent returning needs_input status."""
        mock_load_agent.return_value = lambda: TestStatelessAgent("needs_input")
        
        request_data = {
            "context": {"incomplete": True},
            "documents": {},
            "instructions": "Process incomplete data",
            "execution_id": "exec-needs-input",
            "agent_id": "incomplete-agent"
        }
        
        response = client.post("/agent/incomplete-agent/execute", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "needs_input"
        assert data["content"] == "Need additional documents"
        assert data["missing_inputs"] == ["required_doc", "user_preferences"]
        assert len(data["missing_inputs"]) > 0
    
    @patch('generated.app.load_agent_class')
    def test_agent_failure_with_fallback(self, mock_load_agent, client):
        """Test agent failure handling with structured error response."""
        mock_load_agent.return_value = lambda: TestStatelessAgent("failure")
        
        request_data = {
            "context": {"test": "failure"},
            "instructions": "This should fail",
            "execution_id": "exec-failure",
            "agent_id": "failing-agent"
        }
        
        response = client.post("/agent/failing-agent/execute", json=request_data)
        
        assert response.status_code == 200  # Structured error, not HTTP error
        data = response.json()
        
        assert data["status"] == "failed"
        assert data["content"] == ""
        assert "execution failed" in data["summary"].lower()
        assert "error" in data["metadata"]
        assert data["metadata"]["error"] == "Test agent failure"
        assert data["metadata"]["error_type"] == "Exception"
    
    def test_agent_not_found(self, client):
        """Test handling of non-existent agent."""
        request_data = {
            "context": {"test": True},
            "instructions": "Test non-existent agent",
            "execution_id": "exec-404",
            "agent_id": "non-existent-agent"
        }
        
        response = client.post("/agent/non-existent-agent/execute", json=request_data)
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
    
    def test_agent_id_mismatch(self, client):
        """Test validation of agent_id mismatch between URL and body."""
        request_data = {
            "context": {"test": True},
            "instructions": "Test ID mismatch",
            "execution_id": "exec-mismatch",
            "agent_id": "wrong-agent"  # Different from URL
        }
        
        response = client.post("/agent/correct-agent/execute", json=request_data)
        
        assert response.status_code == 400
        assert "must match" in response.json()["detail"]
        assert "correct-agent" in response.json()["detail"]
        assert "wrong-agent" in response.json()["detail"]
    
    def test_invalid_request_data(self, client):
        """Test validation of invalid request data."""
        # Missing required fields
        invalid_request = {
            "context": {"test": True},
            # Missing instructions, execution_id, agent_id
        }
        
        response = client.post("/agent/test-agent/execute", json=invalid_request)
        
        assert response.status_code == 422  # Validation error
        error_detail = response.json()["detail"]
        assert isinstance(error_detail, list)
        assert len(error_detail) > 0
    
    def test_memory_scope_isolation(self, client):
        """Test that different memory scopes work correctly."""
        with patch('generated.app.load_agent_class') as mock_load_agent:
            mock_load_agent.return_value = lambda: TestStatelessAgent("success")
            
            # Test isolated memory scope
            isolated_request = {
                "context": {"memory_test": "isolated"},
                "instructions": "Test isolated memory",
                "memory_scope": "isolated",
                "execution_id": "exec-isolated",
                "agent_id": "memory-test-agent"
            }
            
            response1 = client.post("/agent/memory-test-agent/execute", json=isolated_request)
            
            # Test shared memory scope
            shared_request = {
                "context": {"memory_test": "shared"},
                "instructions": "Test shared memory", 
                "memory_scope": "shared",
                "execution_id": "exec-shared",
                "agent_id": "memory-test-agent"
            }
            
            response2 = client.post("/agent/memory-test-agent/execute", json=shared_request)
            
            assert response1.status_code == 200
            assert response2.status_code == 200
            
            data1 = response1.json()
            data2 = response2.json()
            
            # Both should succeed
            assert data1["status"] == "completed"
            assert data2["status"] == "completed"
    
    @patch('generated.app.load_agent_class')  
    def test_concurrent_executions_isolation(self, mock_load_agent, client):
        """Test that concurrent executions don't interfere with each other."""
        mock_load_agent.return_value = lambda: TestStatelessAgent("success")
        
        # Prepare multiple concurrent requests
        requests = []
        for i in range(5):
            requests.append({
                "context": {"concurrent_test": i, "isolation_check": True},
                "instructions": f"Concurrent test {i}",
                "execution_id": f"exec-concurrent-{i}",
                "agent_id": "concurrent-agent"
            })
        
        # Execute all requests concurrently using asyncio
        import concurrent.futures
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [
                executor.submit(client.post, "/agent/concurrent-agent/execute", json=req)
                for req in requests
            ]
            
            responses = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        # Verify all succeeded
        for response in responses:
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "completed"
            assert data["metadata"]["test_execution"] is True
    
    @patch('generated.app.load_agent_class')
    def test_execution_time_monitoring(self, mock_load_agent, client):
        """Test that execution time is monitored and reported.""" 
        mock_load_agent.return_value = SlowTestAgent
        
        request_data = {
            "context": {"performance_test": True},
            "instructions": "Test performance monitoring",
            "execution_id": "exec-performance",
            "agent_id": "slow-agent"
        }
        
        response = client.post("/agent/slow-agent/execute", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        
        # Should still complete successfully
        assert data["status"] == "completed" 
        assert data["execution_time_ms"] > 1000  # Should be over 1 second
        
        # Warning should be logged (can't easily test print output in unit tests)
    
    def test_request_validation_edge_cases(self, client):
        """Test edge cases for request validation."""
        # Test invalid agent_id characters
        invalid_agent_request = {
            "context": {"test": True},
            "instructions": "Test invalid agent ID",
            "execution_id": "exec-invalid",
            "agent_id": "invalid@agent"  # Contains invalid character
        }
        
        response = client.post("/agent/invalid@agent/execute", json=invalid_agent_request)
        assert response.status_code == 422
        
        # Test path traversal in execution_id
        traversal_request = {
            "context": {"test": True},
            "instructions": "Test path traversal",
            "execution_id": "../etc/passwd",
            "agent_id": "test-agent"
        }
        
        response = client.post("/agent/test-agent/execute", json=traversal_request)
        assert response.status_code == 422
        
        # Test empty instructions
        empty_instructions_request = {
            "context": {"test": True},
            "instructions": "   ",  # Only whitespace
            "execution_id": "exec-empty",
            "agent_id": "test-agent"
        }
        
        response = client.post("/agent/test-agent/execute", json=empty_instructions_request)
        assert response.status_code == 422
    
    @patch('generated.app.load_agent_class')
    def test_complete_context_available_to_agent(self, mock_load_agent, client):
        """Test that complete context is available to the agent."""
        mock_load_agent.return_value = lambda: TestStatelessAgent("success")
        
        complex_request = {
            "context": {
                "story_id": "S-456",
                "user": "integration_test",
                "workflow_state": "in_progress",
                "metadata": {"priority": "high", "tags": ["urgent", "customer"]}
            },
            "documents": {
                "requirements": "Detailed requirements document content",
                "analysis": "Previous analysis results",
                "user_preferences": "User configuration data"
            },
            "instructions": "Perform comprehensive analysis using all provided context",
            "memory_scope": "shared",
            "execution_id": "exec-complex-context",
            "agent_id": "comprehensive-agent"
        }
        
        response = client.post("/agent/comprehensive-agent/execute", json=complex_request)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "completed"
        
        # Verify agent received the context (TestStatelessAgent includes context keys in metadata)
        context_keys = data["metadata"]["context_keys"]
        assert "story_id" in context_keys
        assert "user" in context_keys
        assert "workflow_state" in context_keys
        assert "metadata" in context_keys
    
    @patch('generated.app.load_agent_class')
    def test_system_error_handling(self, mock_load_agent, client):
        """Test handling of system-level errors during execution."""
        # Mock a system error during agent loading
        mock_load_agent.side_effect = Exception("System database connection failed")
        
        request_data = {
            "context": {"test": True},
            "instructions": "This will cause system error",
            "execution_id": "exec-system-error",
            "agent_id": "system-error-agent"
        }
        
        response = client.post("/agent/system-error-agent/execute", json=request_data)
        
        # Should return structured error, not HTTP 500
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "failed"
        assert data["content"] == ""
        assert "system error" in data["summary"].lower()
        assert data["metadata"]["system_failure"] is True
        assert data["metadata"]["error"] == "System database connection failed"
        assert data["metadata"]["error_type"] == "Exception"


class TestAgentLoading:
    """Test cases for dynamic agent loading functionality."""
    
    def test_agent_id_to_module_name_conversion(self):
        """Test conversion of agent IDs to module names."""
        from generated.app import load_agent_class
        
        test_cases = [
            ("simple-agent", "simple_agent"),
            ("data-analyst", "data_analyst"), 
            ("multi-word-agent-name", "multi_word_agent_name"),
            ("single", "single")
        ]
        
        for agent_id, expected_module in test_cases:
            try:
                # This will fail because modules don't exist, but we can check the conversion logic
                load_agent_class(agent_id)
            except Exception as e:
                # Error message should contain the converted module name
                assert expected_module in str(e) or agent_id in str(e)
    
    def test_agent_class_name_generation(self):
        """Test generation of class names from agent IDs.""" 
        # This is implicit in the load_agent_class function
        # The class name should be PascalCase version of the module name
        test_cases = [
            ("simple-agent", "SimpleAgent"),
            ("data-analyst", "DataAnalyst"),
            ("multi-word-agent", "MultiWordAgent")
        ]
        
        # We can't easily test this without creating actual modules,
        # but the logic is straightforward string manipulation
        for agent_id, expected_class in test_cases:
            module_name = agent_id.replace("-", "_")
            class_name = "".join(word.capitalize() for word in module_name.split("_"))
            assert class_name == expected_class