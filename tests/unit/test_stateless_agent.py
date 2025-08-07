"""Unit tests for stateless agent execution."""

import pytest
import asyncio
from unittest.mock import Mock, patch
from typing import Dict, Any, Tuple

from generated.models import AgentRequest, AgentResponse
from generated.stateless_agent import (
    StatelessAgent, 
    StatelessAgentAsync, 
    ValidationError,
    parse_structured_output,
    check_required_documents
)


class MockStatelessAgent(StatelessAgent):
    """Mock implementation for testing."""
    
    def __init__(self, mock_result=None, should_fail=False):
        super().__init__(max_retries=3, wait=0)
        self.mock_result = mock_result or {
            "status": "completed",
            "content": "Test completed",
            "summary": "Mock test execution"
        }
        self.should_fail = should_fail
        self.exec_call_count = 0
    
    def exec(self, prep_res: Tuple[AgentRequest, Dict[str, Any], int]) -> Dict[str, Any]:
        """Mock exec implementation."""
        self.exec_call_count += 1
        
        if self.should_fail:
            raise Exception("Mock failure")
        
        agent_request, memory_context, start_time = prep_res
        
        # Add execution metadata
        result = self.mock_result.copy()
        result.setdefault("metadata", {})
        result["metadata"]["agent_id"] = agent_request.agent_id
        result["metadata"]["execution_id"] = agent_request.execution_id
        
        return result


class MockStatelessAgentAsync(StatelessAgentAsync):
    """Mock async implementation for testing."""
    
    def __init__(self, mock_result=None, should_fail=False):
        super().__init__(max_retries=3, wait=0)
        self.mock_result = mock_result or {
            "status": "completed",
            "content": "Async test completed",
            "summary": "Mock async test execution"
        }
        self.should_fail = should_fail
        self.exec_call_count = 0
    
    async def exec_async(self, prep_res: Tuple[AgentRequest, Dict[str, Any], int]) -> Dict[str, Any]:
        """Mock async exec implementation."""
        self.exec_call_count += 1
        
        if self.should_fail:
            raise Exception("Mock async failure")
        
        await asyncio.sleep(0.001)  # Simulate async work
        
        agent_request, memory_context, start_time = prep_res
        
        result = self.mock_result.copy()
        result.setdefault("metadata", {})
        result["metadata"]["agent_id"] = agent_request.agent_id
        result["metadata"]["execution_id"] = agent_request.execution_id
        
        return result


class TestStatelessAgent:
    """Test cases for StatelessAgent base class."""
    
    def test_complete_context_passed_to_agent(self):
        """Test that complete context is passed to agent execution."""
        agent = MockStatelessAgent()
        
        request = AgentRequest(
            context={"story_id": "S-123", "user": "test"},
            documents={"doc1": "content1"},
            instructions="Process data",
            execution_id="exec-001",
            agent_id="test-agent"
        )
        
        shared = {
            "agent_request": request,
            "shared_memory": {"previous_result": "data"}
        }
        
        response = agent.run(shared)
        
        # Verify response structure
        assert isinstance(response, AgentResponse)
        assert response.status == "completed"
        assert response.content == "Test completed"
        assert response.metadata["agent_id"] == "test-agent"
        assert response.metadata["execution_id"] == "exec-001"
    
    def test_identical_inputs_produce_identical_outputs(self):
        """Test that identical inputs produce identical outputs (stateless behavior)."""
        agent1 = MockStatelessAgent()
        agent2 = MockStatelessAgent()
        
        request = AgentRequest(
            context={"task": "analyze"},
            documents={"doc1": "same content"},
            instructions="Same instructions",
            execution_id="exec-identical",
            agent_id="test-agent"
        )
        
        shared1 = {"agent_request": request}
        shared2 = {"agent_request": request}  # Identical
        
        response1 = agent1.run(shared1)
        response2 = agent2.run(shared2)
        
        # Responses should be identical (excluding execution_time_ms)
        assert response1.status == response2.status
        assert response1.content == response2.content
        assert response1.summary == response2.summary
        assert response1.metadata["agent_id"] == response2.metadata["agent_id"]
    
    def test_no_state_persists_between_calls(self):
        """Test that no state persists between agent calls."""
        agent = MockStatelessAgent()
        
        # First call
        request1 = AgentRequest(
            context={"call": "first"},
            instructions="First call",
            execution_id="exec-001", 
            agent_id="test-agent"
        )
        shared1 = {"agent_request": request1}
        response1 = agent.run(shared1)
        
        # Second call with different context
        request2 = AgentRequest(
            context={"call": "second"},
            instructions="Second call",
            execution_id="exec-002",
            agent_id="test-agent"
        )
        shared2 = {"agent_request": request2}
        response2 = agent.run(shared2)
        
        # Verify both calls succeeded independently
        assert response1.status == "completed"
        assert response2.status == "completed"
        assert response1.metadata["execution_id"] == "exec-001"
        assert response2.metadata["execution_id"] == "exec-002"
        
        # Verify exec was called for each
        assert agent.exec_call_count == 2
    
    def test_needs_input_with_missing_requirements(self):
        """Test needs_input status with missing requirements list."""
        mock_result = {
            "status": "needs_input",
            "content": "Need more documents",
            "summary": "Missing required documents",
            "missing_inputs": ["document_a", "user_preference"]
        }
        
        agent = MockStatelessAgent(mock_result=mock_result)
        
        request = AgentRequest(
            context={"task": "incomplete"},
            instructions="Process incomplete data",
            execution_id="exec-needs-input",
            agent_id="test-agent"
        )
        
        shared = {"agent_request": request}
        response = agent.run(shared)
        
        assert response.status == "needs_input"
        assert response.missing_inputs == ["document_a", "user_preference"]
        assert len(response.missing_inputs) > 0
    
    def test_failed_execution_returns_error_details(self):
        """Test that failed execution returns structured error information."""
        agent = MockStatelessAgent(should_fail=True)
        
        request = AgentRequest(
            context={"task": "fail"},
            instructions="This will fail",
            execution_id="exec-fail",
            agent_id="test-agent"
        )
        
        shared = {"agent_request": request}
        response = agent.run(shared)
        
        # Should use fallback
        assert response.status == "failed"
        assert response.content == ""
        assert "execution failed" in response.summary.lower()
        assert "error" in response.metadata
        assert "error_type" in response.metadata
        assert response.metadata["error"] == "Mock failure"
        assert response.metadata["error_type"] == "Exception"
    
    def test_execution_completes_under_1_second(self):
        """Test that execution completes under 1 second."""
        agent = MockStatelessAgent()
        
        request = AgentRequest(
            context={"task": "fast"},
            instructions="Fast execution",
            execution_id="exec-fast",
            agent_id="test-agent"
        )
        
        shared = {"agent_request": request}
        response = agent.run(shared)
        
        assert response.execution_time_ms is not None
        assert response.execution_time_ms < 1000  # Sub-1s requirement
    
    def test_memory_isolation_between_executions(self):
        """Test memory isolation between different execution IDs."""
        agent = MockStatelessAgent()
        
        # Create requests with different memory scopes
        request_isolated = AgentRequest(
            context={"test": "isolated"},
            instructions="Isolated test",
            execution_id="exec-isolated",
            agent_id="test-agent",
            memory_scope="isolated"
        )
        
        request_shared = AgentRequest(
            context={"test": "shared"},
            instructions="Shared test",
            execution_id="exec-shared", 
            agent_id="test-agent",
            memory_scope="shared"
        )
        
        # Set up different memory contexts
        shared1 = {
            "agent_request": request_isolated,
            "memory_test-agent_exec-isolated": {"isolated_data": "private"}
        }
        
        shared2 = {
            "agent_request": request_shared,
            "shared_memory": {"shared_data": "public"}
        }
        
        response1 = agent.run(shared1)
        response2 = agent.run(shared2)
        
        # Both should succeed independently
        assert response1.status == "completed"
        assert response2.status == "completed"
        assert response1.metadata["execution_id"] != response2.metadata["execution_id"]
    
    def test_validation_of_structured_response(self):
        """Test validation of structured response format."""
        # Test invalid status
        invalid_result = {
            "status": "invalid_status",
            "content": "test",
            "summary": "test"
        }
        agent = MockStatelessAgent(mock_result=invalid_result)
        
        request = AgentRequest(
            context={"test": True},
            instructions="Test validation",
            execution_id="exec-validation",
            agent_id="test-agent"
        )
        
        shared = {"agent_request": request}
        
        with pytest.raises(ValidationError, match="Invalid status"):
            agent.run(shared)
    
    def test_retry_mechanism(self):
        """Test that retry mechanism works correctly."""
        agent = MockStatelessAgent(should_fail=True)
        agent.max_retries = 3
        
        request = AgentRequest(
            context={"test": "retry"},
            instructions="Test retry",
            execution_id="exec-retry",
            agent_id="test-agent"
        )
        
        shared = {"agent_request": request}
        response = agent.run(shared)
        
        # Should have tried 3 times then used fallback
        assert agent.exec_call_count == 3
        assert response.status == "failed"
        assert response.metadata["retry_count"] == 2  # 0-indexed


class TestStatelessAgentAsync:
    """Test cases for StatelessAgentAsync."""
    
    @pytest.mark.asyncio
    async def test_async_execution_pattern(self):
        """Test async execution pattern works correctly."""
        agent = MockStatelessAgentAsync()
        
        request = AgentRequest(
            context={"async": True},
            instructions="Async test",
            execution_id="exec-async",
            agent_id="async-agent"
        )
        
        shared = {"agent_request": request}
        response = await agent.run_async(shared)
        
        assert isinstance(response, AgentResponse)
        assert response.status == "completed"
        assert response.content == "Async test completed"
        assert response.execution_time_ms < 1000
    
    @pytest.mark.asyncio
    async def test_async_concurrent_executions_dont_interfere(self):
        """Test that concurrent async executions don't interfere."""
        agent1 = MockStatelessAgentAsync()
        agent2 = MockStatelessAgentAsync()
        
        request1 = AgentRequest(
            context={"concurrent": 1},
            instructions="First concurrent",
            execution_id="exec-concurrent-1",
            agent_id="agent-1"
        )
        
        request2 = AgentRequest(
            context={"concurrent": 2},
            instructions="Second concurrent",
            execution_id="exec-concurrent-2",
            agent_id="agent-2"
        )
        
        shared1 = {"agent_request": request1}
        shared2 = {"agent_request": request2}
        
        # Run concurrently
        response1, response2 = await asyncio.gather(
            agent1.run_async(shared1),
            agent2.run_async(shared2)
        )
        
        # Both should succeed independently
        assert response1.status == "completed"
        assert response2.status == "completed"
        assert response1.metadata["execution_id"] == "exec-concurrent-1"
        assert response2.metadata["execution_id"] == "exec-concurrent-2"
        assert response1.metadata["agent_id"] == "agent-1"
        assert response2.metadata["agent_id"] == "agent-2"


class TestStructuredOutputParsing:
    """Test cases for structured output parsing utilities."""
    
    def test_parse_valid_yaml_output(self):
        """Test parsing valid YAML output from LLM."""
        llm_response = """Here's the analysis:
        
```yaml
status: completed
content: Analysis complete
summary: Found key insights
metadata:
  insights: 5
  confidence: 0.95
```

The analysis is complete."""
        
        result = parse_structured_output(llm_response)
        
        assert result["status"] == "completed"
        assert result["content"] == "Analysis complete"
        assert result["metadata"]["insights"] == 5
        assert result["metadata"]["confidence"] == 0.95
    
    def test_parse_yaml_with_multiline_content(self):
        """Test parsing YAML with multiline content."""
        llm_response = """
```yaml
status: completed
content: |
  This is a multiline
  content with line breaks
  and proper formatting
summary: Multiline test
```
"""
        
        result = parse_structured_output(llm_response)
        
        assert "multiline" in result["content"].lower()
        assert "line breaks" in result["content"]
    
    def test_parse_missing_yaml_block(self):
        """Test error handling when YAML block is missing."""
        llm_response = "No YAML block here, just plain text."
        
        with pytest.raises(ValidationError, match="No YAML code block found"):
            parse_structured_output(llm_response)
    
    def test_parse_invalid_yaml_syntax(self):
        """Test error handling for invalid YAML syntax."""
        llm_response = """
        ```yaml
        status: completed
        content: "unterminated string
        summary: invalid
        ```
        """
        
        with pytest.raises(ValidationError, match="YAML parsing error"):
            parse_structured_output(llm_response)
    
    def test_parse_empty_yaml_block(self):
        """Test error handling for empty YAML block.""" 
        llm_response = """
        ```yaml
        ```
        """
        
        with pytest.raises(ValidationError, match="Empty YAML block"):
            parse_structured_output(llm_response)


class TestDocumentChecking:
    """Test cases for document availability checking."""
    
    def test_all_required_documents_available(self):
        """Test when all required documents are available."""
        documents = {
            "doc1": "content1",
            "doc2": "content2", 
            "doc3": "content3"
        }
        required = ["doc1", "doc2"]
        
        missing = check_required_documents(documents, required)
        
        assert missing == []
    
    def test_some_required_documents_missing(self):
        """Test when some required documents are missing."""
        documents = {
            "doc1": "content1",
            "doc3": "content3"
        }
        required = ["doc1", "doc2", "doc4"]
        
        missing = check_required_documents(documents, required)
        
        assert set(missing) == {"doc2", "doc4"}
    
    def test_empty_document_content_considered_missing(self):
        """Test that empty document content is considered missing."""
        documents = {
            "doc1": "content1",
            "doc2": "",  # Empty
            "doc3": "   ",  # Only whitespace
            "doc4": "content4"
        }
        required = ["doc1", "doc2", "doc3", "doc4"]
        
        missing = check_required_documents(documents, required)
        
        assert set(missing) == {"doc2", "doc3"}
    
    def test_no_required_documents(self):
        """Test when no documents are required."""
        documents = {"doc1": "content1"}
        required = []
        
        missing = check_required_documents(documents, required)
        
        assert missing == []