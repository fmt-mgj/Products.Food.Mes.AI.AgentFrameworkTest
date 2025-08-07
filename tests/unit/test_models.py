import pytest
from datetime import datetime
from pydantic import ValidationError

from generated.models import AgentStatus, WorkflowStatus, WorkflowListItem


class TestAgentStatus:
    """Test AgentStatus model validation."""

    def test_valid_agent_status(self):
        """Test creating valid AgentStatus instance."""
        status = AgentStatus(
            status="completed",
            last_execution=datetime.now(),
            output_summary="Task completed successfully"
        )
        assert status.status == "completed"
        assert status.last_execution is not None
        assert status.output_summary == "Task completed successfully"

    def test_valid_status_values(self):
        """Test all valid status values are accepted."""
        valid_statuses = ["pending", "running", "completed", "failed", "needs_input"]
        for status_value in valid_statuses:
            status = AgentStatus(status=status_value)
            assert status.status == status_value

    def test_invalid_status_value(self):
        """Test invalid status value raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            AgentStatus(status="invalid_status")
        
        assert "status" in str(exc_info.value)

    def test_optional_fields_default_none(self):
        """Test optional fields default to None."""
        status = AgentStatus(status="pending")
        assert status.last_execution is None
        assert status.output_summary is None


class TestWorkflowStatus:
    """Test WorkflowStatus model validation."""

    def test_valid_workflow_status(self):
        """Test creating valid WorkflowStatus instance."""
        agent_status = AgentStatus(status="completed")
        workflow = WorkflowStatus(
            workflow_id="test-workflow-123",
            agent_statuses={"agent1": agent_status}
        )
        assert workflow.workflow_id == "test-workflow-123"
        assert "agent1" in workflow.agent_statuses
        assert workflow.agent_statuses["agent1"].status == "completed"

    def test_valid_workflow_ids(self):
        """Test valid workflow ID formats."""
        valid_ids = ["test", "test-123", "test_456", "ABC-123_def"]
        for workflow_id in valid_ids:
            workflow = WorkflowStatus(
                workflow_id=workflow_id,
                agent_statuses={}
            )
            assert workflow.workflow_id == workflow_id

    def test_invalid_workflow_id_path_traversal(self):
        """Test workflow ID validation prevents path traversal."""
        invalid_ids = ["../test", "test/../other", "test/sub", "test\\sub"]
        for workflow_id in invalid_ids:
            with pytest.raises(ValidationError) as exc_info:
                WorkflowStatus(
                    workflow_id=workflow_id,
                    agent_statuses={}
                )
            assert "Invalid workflow ID" in str(exc_info.value)

    def test_invalid_workflow_id_special_chars(self):
        """Test workflow ID validation rejects special characters."""
        invalid_ids = ["test@123", "test#123", "test!123", "test space"]
        for workflow_id in invalid_ids:
            with pytest.raises(ValidationError) as exc_info:
                WorkflowStatus(
                    workflow_id=workflow_id,
                    agent_statuses={}
                )
            assert "Workflow ID must be alphanumeric" in str(exc_info.value)

    def test_empty_agent_statuses(self):
        """Test WorkflowStatus with empty agent_statuses."""
        workflow = WorkflowStatus(
            workflow_id="empty-workflow",
            agent_statuses={}
        )
        assert workflow.agent_statuses == {}


class TestWorkflowListItem:
    """Test WorkflowListItem model."""

    def test_valid_workflow_list_item(self):
        """Test creating valid WorkflowListItem instance."""
        now = datetime.now()
        item = WorkflowListItem(
            workflow_id="test-workflow",
            last_update=now
        )
        assert item.workflow_id == "test-workflow"
        assert item.last_update == now