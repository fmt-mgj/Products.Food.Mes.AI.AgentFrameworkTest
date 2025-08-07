"""Simplified integration tests for orchestrator status functionality."""

import json
import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from generated.models import AgentStatus, WorkflowStatus
from generated.orchestrator_status import StatusService


class TestStatusServiceIntegration:
    """Integration tests for StatusService focusing on core functionality."""

    @pytest.fixture
    def temp_storage(self):
        """Create temporary storage directory for tests."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir

    @pytest.fixture
    def status_service(self, temp_storage):
        """Create StatusService with temporary storage."""
        return StatusService(storage_dir=temp_storage)

    @pytest.mark.asyncio
    async def test_write_and_read_status_workflow(self, status_service):
        """Test complete workflow: create, update, and read status."""
        workflow_id = "integration-test"
        
        # Create initial status
        initial_status = WorkflowStatus(
            workflow_id=workflow_id,
            agent_statuses={
                "agent1": AgentStatus(status="pending"),
                "agent2": AgentStatus(status="pending")
            }
        )
        
        await status_service.write_status(initial_status)
        
        # Verify it can be read
        result = await status_service.read_status(workflow_id)
        assert result is not None
        assert result.workflow_id == workflow_id
        assert len(result.agent_statuses) == 2
        assert result.agent_statuses["agent1"].status == "pending"
        
        # Update one agent
        updated_status = WorkflowStatus(
            workflow_id=workflow_id,
            agent_statuses={
                "agent1": AgentStatus(status="completed", output_summary="Done"),
                "agent2": AgentStatus(status="running")
            }
        )
        
        await status_service.write_status(updated_status)
        
        # Verify updated status
        final_result = await status_service.read_status(workflow_id)
        assert final_result is not None
        assert final_result.agent_statuses["agent1"].status == "completed"
        assert final_result.agent_statuses["agent1"].output_summary == "Done"
        assert final_result.agent_statuses["agent2"].status == "running"

    @pytest.mark.asyncio
    async def test_multiple_workflows_isolation(self, status_service):
        """Test that multiple workflows don't interfere with each other."""
        # Create two different workflows
        workflow1 = WorkflowStatus(
            workflow_id="workflow-1",
            agent_statuses={"agent1": AgentStatus(status="completed")}
        )
        
        workflow2 = WorkflowStatus(
            workflow_id="workflow-2", 
            agent_statuses={"agent1": AgentStatus(status="failed")}
        )
        
        await status_service.write_status(workflow1)
        await status_service.write_status(workflow2)
        
        # Read both and verify they're independent
        result1 = await status_service.read_status("workflow-1")
        result2 = await status_service.read_status("workflow-2")
        
        assert result1.agent_statuses["agent1"].status == "completed"
        assert result2.agent_statuses["agent1"].status == "failed"

    @pytest.mark.asyncio
    async def test_list_workflows_functionality(self, status_service):
        """Test workflow listing functionality."""
        # Create multiple workflows
        workflows = ["list-test-1", "list-test-2", "list-test-3"]
        
        for workflow_id in workflows:
            status = WorkflowStatus(
                workflow_id=workflow_id,
                agent_statuses={"agent1": AgentStatus(status="pending")}
            )
            await status_service.write_status(status)
        
        # List workflows
        workflow_list = await status_service.list_workflows()
        
        # Verify all workflows are listed
        workflow_ids = [item.workflow_id for item in workflow_list]
        for workflow_id in workflows:
            assert workflow_id in workflow_ids

    @pytest.mark.asyncio
    async def test_nonexistent_workflow_returns_none(self, status_service):
        """Test that reading non-existent workflow returns None."""
        result = await status_service.read_status("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_jsonl_history_preservation(self, status_service):
        """Test that JSONL history is preserved correctly."""
        workflow_id = "history-test"
        
        # Create multiple status updates
        statuses = [
            WorkflowStatus(workflow_id=workflow_id, agent_statuses={"agent1": AgentStatus(status="pending")}),
            WorkflowStatus(workflow_id=workflow_id, agent_statuses={"agent1": AgentStatus(status="running")}),
            WorkflowStatus(workflow_id=workflow_id, agent_statuses={"agent1": AgentStatus(status="completed")})
        ]
        
        for status in statuses:
            await status_service.write_status(status)
        
        # Verify file contains all updates
        file_path = status_service._get_status_file_path(workflow_id)
        with open(file_path, 'r') as f:
            lines = f.readlines()
        
        assert len(lines) == 3
        
        # Verify progression
        first_record = json.loads(lines[0])
        last_record = json.loads(lines[-1])
        
        assert first_record["agent_statuses"]["agent1"]["status"] == "pending"
        assert last_record["agent_statuses"]["agent1"]["status"] == "completed"
        
        # But read_status should return only the latest
        latest = await status_service.read_status(workflow_id)
        assert latest.agent_statuses["agent1"].status == "completed"

    @pytest.mark.asyncio
    async def test_all_status_values_valid(self, status_service):
        """Test that all valid status values work correctly."""
        valid_statuses = ["pending", "running", "completed", "failed", "needs_input"]
        workflow_id = "status-validation-test"
        
        for status_value in valid_statuses:
            workflow_status = WorkflowStatus(
                workflow_id=workflow_id,
                agent_statuses={"agent1": AgentStatus(status=status_value)}
            )
            
            await status_service.write_status(workflow_status)
            result = await status_service.read_status(workflow_id)
            
            assert result.agent_statuses["agent1"].status == status_value

    def test_workflow_id_validation(self):
        """Test workflow ID validation prevents malicious inputs."""
        with pytest.raises(ValueError, match="Invalid workflow ID"):
            WorkflowStatus(
                workflow_id="../malicious",
                agent_statuses={"agent1": AgentStatus(status="pending")}
            )
        
        with pytest.raises(ValueError, match="Workflow ID must be alphanumeric"):
            WorkflowStatus(
                workflow_id="test@malicious",
                agent_statuses={"agent1": AgentStatus(status="pending")}
            )