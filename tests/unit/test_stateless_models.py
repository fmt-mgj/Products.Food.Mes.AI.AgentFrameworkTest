"""Unit tests for stateless execution models."""

import pytest
from pydantic import ValidationError

from generated.models import AgentRequest, AgentResponse


class TestAgentRequest:
    """Test cases for AgentRequest model validation."""
    
    def test_valid_request_minimal(self):
        """Test minimal valid AgentRequest."""
        request = AgentRequest(
            context={"story_id": "S-123"},
            instructions="Analyze the data",
            execution_id="exec-001",
            agent_id="analyst"
        )
        
        assert request.context == {"story_id": "S-123"}
        assert request.instructions == "Analyze the data"
        assert request.execution_id == "exec-001"
        assert request.agent_id == "analyst"
        assert request.memory_scope == "isolated"
        assert request.documents == {}
    
    def test_valid_request_complete(self):
        """Test complete valid AgentRequest with all fields."""
        request = AgentRequest(
            context={"story_id": "S-123", "user": "test"},
            documents={"doc1": "content1", "doc2": "content2"},
            instructions="Process documents",
            memory_scope="shared",
            execution_id="exec-002",
            agent_id="processor"
        )
        
        assert request.context == {"story_id": "S-123", "user": "test"}
        assert request.documents == {"doc1": "content1", "doc2": "content2"}
        assert request.memory_scope == "shared"
    
    def test_invalid_execution_id_path_traversal(self):
        """Test that execution_id with path separators is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            AgentRequest(
                context={"story_id": "S-123"},
                instructions="Test",
                execution_id="../bad",
                agent_id="test"
            )
        
        assert "path separators not allowed" in str(exc_info.value)
    
    def test_invalid_agent_id_special_chars(self):
        """Test that agent_id with special characters is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            AgentRequest(
                context={"story_id": "S-123"},
                instructions="Test",
                execution_id="exec-001",
                agent_id="agent@bad"
            )
        
        assert "must be alphanumeric" in str(exc_info.value)
    
    def test_empty_instructions(self):
        """Test that empty instructions are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            AgentRequest(
                context={"story_id": "S-123"},
                instructions="   ",
                execution_id="exec-001",
                agent_id="test"
            )
        
        assert "Instructions cannot be empty" in str(exc_info.value)
    
    def test_instructions_trimmed(self):
        """Test that instructions are trimmed of whitespace."""
        request = AgentRequest(
            context={"story_id": "S-123"},
            instructions="  Test instructions  ",
            execution_id="exec-001",
            agent_id="test"
        )
        
        assert request.instructions == "Test instructions"
    
    def test_valid_ids_with_underscores_and_dashes(self):
        """Test that IDs with underscores and dashes are valid."""
        request = AgentRequest(
            context={"story_id": "S-123"},
            instructions="Test",
            execution_id="exec_001-test",
            agent_id="agent_name-v2"
        )
        
        assert request.execution_id == "exec_001-test"
        assert request.agent_id == "agent_name-v2"


class TestAgentResponse:
    """Test cases for AgentResponse model validation."""
    
    def test_valid_response_completed(self):
        """Test valid completed response."""
        response = AgentResponse(
            status="completed",
            content="Task completed successfully",
            summary="Processed all data"
        )
        
        assert response.status == "completed"
        assert response.content == "Task completed successfully"
        assert response.summary == "Processed all data"
        assert response.missing_inputs == []
        assert response.metadata == {}
    
    def test_valid_response_needs_input(self):
        """Test valid needs_input response."""
        response = AgentResponse(
            status="needs_input",
            content="Partial analysis completed",
            summary="Need additional documents",
            missing_inputs=["document_a", "user_preference"]
        )
        
        assert response.status == "needs_input"
        assert response.missing_inputs == ["document_a", "user_preference"]
    
    def test_valid_response_failed(self):
        """Test valid failed response."""
        response = AgentResponse(
            status="failed",
            content="",
            summary="Execution failed",
            metadata={"error": "Connection timeout", "retry_count": 3}
        )
        
        assert response.status == "failed"
        assert response.metadata["error"] == "Connection timeout"
    
    def test_invalid_needs_input_without_missing_inputs(self):
        """Test that needs_input status requires missing_inputs to be populated."""
        with pytest.raises(ValidationError) as exc_info:
            AgentResponse(
                status="needs_input",
                content="Need more data",
                summary="Missing information"
            )
        
        assert "missing_inputs cannot be empty when status is needs_input" in str(exc_info.value)
    
    def test_response_with_execution_time(self):
        """Test response with execution time metadata."""
        response = AgentResponse(
            status="completed",
            content="Task done",
            summary="Success",
            execution_time_ms=450
        )
        
        assert response.execution_time_ms == 450
    
    def test_invalid_status_value(self):
        """Test that invalid status values are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            AgentResponse(
                status="invalid_status",
                content="Test",
                summary="Test"
            )
        
        assert "Input should be 'completed', 'needs_input' or 'failed'" in str(exc_info.value)


class TestModelIntegration:
    """Integration tests for model interaction."""
    
    def test_request_response_roundtrip(self):
        """Test that request can generate appropriate response."""
        request = AgentRequest(
            context={"task": "analyze"},
            documents={"doc1": "data"},
            instructions="Process the document",
            execution_id="exec-roundtrip",
            agent_id="analyzer"
        )
        
        # Simulate successful execution
        response = AgentResponse(
            status="completed",
            content="Analysis complete: Found 5 key points",
            summary="Document analyzed successfully",
            metadata={"points_found": 5, "confidence": 0.95},
            execution_time_ms=250
        )
        
        # Verify the models work together
        assert request.agent_id == "analyzer"
        assert response.status == "completed"
        assert response.execution_time_ms < 1000  # Sub-1s requirement
    
    def test_memory_scope_options(self):
        """Test all valid memory scope options."""
        for scope in ["isolated", "shared"]:
            request = AgentRequest(
                context={"test": True},
                instructions="Test",
                execution_id=f"exec-{scope}",
                agent_id="test",
                memory_scope=scope
            )
            assert request.memory_scope == scope