import asyncio
import json
import tempfile
from datetime import datetime
from pathlib import Path

import pytest
import httpx
from httpx import ASGITransport

# Import the app directly - avoid version issues with test client fixtures
try:
    from generated.app import app
    from generated.models import AgentStatus, WorkflowStatus
    from generated.orchestrator_status import StatusService
except ImportError:
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent.parent / "generated"))
    from app import app
    from models import AgentStatus, WorkflowStatus
    from orchestrator_status import StatusService


@pytest.fixture
def temp_storage():
    """Create temporary storage directory for tests."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir


@pytest.fixture
def status_service_with_temp_storage(temp_storage):
    """Create StatusService with temporary storage."""
    return StatusService(storage_dir=temp_storage)


class TestGetStatusEndpoint:
    """Test GET /orchestration/status/{workflow_id} endpoint."""

    @pytest.mark.asyncio
    async def test_get_status_returns_latest(self, status_service_with_temp_storage):
        """Test that GET status returns the latest status from JSONL."""
        workflow_id = "test-workflow"
        
        # Create initial status
        initial_status = WorkflowStatus(
            workflow_id=workflow_id,
            agent_statuses={"agent1": AgentStatus(status="running")}
        )
        await status_service_with_temp_storage.write_status(initial_status)
        
        # Update status
        updated_status = WorkflowStatus(
            workflow_id=workflow_id,
            agent_statuses={"agent1": AgentStatus(status="completed", output_summary="Done")}
        )
        await status_service_with_temp_storage.write_status(updated_status)
        
        # Read status should return latest
        result = await status_service_with_temp_storage.read_status(workflow_id)
        assert result is not None
        assert result.agent_statuses["agent1"].status == "completed"
        assert result.agent_statuses["agent1"].output_summary == "Done"

    def test_get_status_not_found_returns_404(self):
        """Test that GET status for non-existent workflow returns 404."""
        transport = ASGITransport(app=app)
        with httpx.Client(transport=transport, base_url="http://test") as client:
            response = client.get("/orchestration/status/non-existent-workflow")
            assert response.status_code == 404
            assert "not found" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_get_status_via_api(self):
        """Test GET status via FastAPI endpoint."""
        transport = ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
            # First, create a workflow status
            workflow_status = {
                "workflow_id": "api-test",
                "agent_statuses": {
                    "agent1": {
                        "status": "completed",
                        "last_execution": datetime.now().isoformat(),
                        "output_summary": "API test successful"
                    }
                }
            }
            
            # PUT the status first
            put_response = await ac.put(
                "/orchestration/status/api-test",
                json=workflow_status
            )
            assert put_response.status_code == 200
            
            # Now GET the status
            get_response = await ac.get("/orchestration/status/api-test")
            assert get_response.status_code == 200
            
            data = get_response.json()
            assert data["workflow_id"] == "api-test"
            assert data["agent_statuses"]["agent1"]["status"] == "completed"
            assert data["agent_statuses"]["agent1"]["output_summary"] == "API test successful"


class TestPutStatusEndpoint:
    """Test PUT /orchestration/status/{workflow_id} endpoint."""

    @pytest.mark.asyncio
    async def test_put_status_creates_new_workflow(self):
        """Test that PUT status creates new workflow if it doesn't exist."""
        workflow_status = {
            "workflow_id": "new-workflow",
            "agent_statuses": {
                "agent1": {"status": "pending"},
                "agent2": {"status": "running", "output_summary": "In progress"}
            }
        }
        
        transport = ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
            response = await ac.put(
                "/orchestration/status/new-workflow",
                json=workflow_status
            )
            assert response.status_code == 200
            
            data = response.json()
            assert data["workflow_id"] == "new-workflow"
            assert len(data["agent_statuses"]) == 2

    @pytest.mark.asyncio
    async def test_put_status_updates_existing_workflow(self):
        """Test that PUT status updates existing workflow."""
        workflow_id = "existing-workflow"
        
        transport = ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
            # Create initial status
            initial_status = {
                "workflow_id": workflow_id,
                "agent_statuses": {"agent1": {"status": "pending"}}
            }
            await ac.put(f"/orchestration/status/{workflow_id}", json=initial_status)
            
            # Update status
            updated_status = {
                "workflow_id": workflow_id,
                "agent_statuses": {"agent1": {"status": "completed", "output_summary": "Updated"}}
            }
            response = await ac.put(f"/orchestration/status/{workflow_id}", json=updated_status)
            assert response.status_code == 200
            
            # Verify update
            get_response = await ac.get(f"/orchestration/status/{workflow_id}")
            data = get_response.json()
            assert data["agent_statuses"]["agent1"]["status"] == "completed"
            assert data["agent_statuses"]["agent1"]["output_summary"] == "Updated"

    @pytest.mark.asyncio
    async def test_put_status_mismatched_id_returns_400(self):
        """Test that PUT status with mismatched workflow_id returns 400."""
        workflow_status = {
            "workflow_id": "different-id",
            "agent_statuses": {"agent1": {"status": "pending"}}
        }
        
        transport = ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
            response = await ac.put(
                "/orchestration/status/url-id",
                json=workflow_status
            )
            assert response.status_code == 400
            assert "must match" in response.json()["detail"]


class TestListWorkflowsEndpoint:
    """Test GET /orchestration/workflows endpoint."""

    @pytest.mark.asyncio
    async def test_list_workflows_returns_all(self):
        """Test that list workflows returns all workflows."""
        transport = ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
            # Create multiple workflows
            workflows = ["workflow-1", "workflow-2", "workflow-3"]
            for workflow_id in workflows:
                workflow_status = {
                    "workflow_id": workflow_id,
                    "agent_statuses": {"agent1": {"status": "pending"}}
                }
                await ac.put(f"/orchestration/status/{workflow_id}", json=workflow_status)
            
            # List workflows
            response = await ac.get("/orchestration/workflows")
            assert response.status_code == 200
            
            data = response.json()
            assert len(data) >= 3
            workflow_ids = [item["workflow_id"] for item in data]
            for workflow_id in workflows:
                assert workflow_id in workflow_ids


class TestInvalidInputValidation:
    """Test validation of invalid inputs."""

    @pytest.mark.asyncio
    async def test_invalid_workflow_id_rejected(self):
        """Test that invalid workflow IDs are rejected."""
        invalid_ids = ["../test", "test/sub", "test@123"]
        
        transport = ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
            for invalid_id in invalid_ids:
                workflow_status = {
                    "workflow_id": invalid_id,
                    "agent_statuses": {"agent1": {"status": "pending"}}
                }
                response = await ac.put(
                    f"/orchestration/status/{invalid_id}",
                    json=workflow_status
                )
                # Should return 422 (validation error) due to Pydantic validation
                assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_invalid_status_value_rejected(self):
        """Test that invalid status values are rejected."""
        workflow_status = {
            "workflow_id": "test-workflow",
            "agent_statuses": {"agent1": {"status": "invalid_status"}}
        }
        
        transport = ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
            response = await ac.put(
                "/orchestration/status/test-workflow",
                json=workflow_status
            )
            # Should return 422 due to invalid status value
            assert response.status_code == 422


class TestJSONLPersistence:
    """Test JSONL file persistence behavior."""

    @pytest.mark.asyncio
    async def test_jsonl_append_maintains_history(self, status_service_with_temp_storage):
        """Test that JSONL append mode maintains update history."""
        workflow_id = "history-test"
        
        # Create multiple status updates
        statuses = [
            WorkflowStatus(workflow_id=workflow_id, agent_statuses={"agent1": AgentStatus(status="pending")}),
            WorkflowStatus(workflow_id=workflow_id, agent_statuses={"agent1": AgentStatus(status="running")}),
            WorkflowStatus(workflow_id=workflow_id, agent_statuses={"agent1": AgentStatus(status="completed")})
        ]
        
        for status in statuses:
            await status_service_with_temp_storage.write_status(status)
        
        # Read file directly to verify history
        file_path = status_service_with_temp_storage._get_status_file_path(workflow_id)
        with open(file_path, 'r') as f:
            lines = f.readlines()
        
        assert len(lines) == 3
        
        # Verify the progression
        first_status = json.loads(lines[0])
        last_status = json.loads(lines[-1])
        
        assert first_status["agent_statuses"]["agent1"]["status"] == "pending"
        assert last_status["agent_statuses"]["agent1"]["status"] == "completed"


class TestConcurrentAccess:
    """Test concurrent workflow access."""

    @pytest.mark.asyncio
    async def test_concurrent_workflow_updates(self):
        """Test that concurrent workflow updates work correctly."""
        transport = ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
            # Create tasks for concurrent updates
            async def update_workflow(workflow_id: str, status: str):
                workflow_status = {
                    "workflow_id": workflow_id,
                    "agent_statuses": {"agent1": {"status": status}}
                }
                return await ac.put(f"/orchestration/status/{workflow_id}", json=workflow_status)
            
            # Run concurrent updates
            tasks = [
                update_workflow("concurrent-1", "pending"),
                update_workflow("concurrent-2", "running"),
                update_workflow("concurrent-3", "completed")
            ]
            
            results = await asyncio.gather(*tasks)
            
            # All should succeed
            for result in results:
                assert result.status_code == 200


class TestOpenAPIDocumentation:
    """Test OpenAPI documentation generation."""

    def test_openapi_documentation_generated(self):
        """Test that OpenAPI docs are properly generated."""
        transport = ASGITransport(app=app)
        with httpx.Client(transport=transport, base_url="http://test") as client:
            response = client.get("/openapi.json")
            assert response.status_code == 200
            
            openapi_spec = response.json()
            
            # Check that our endpoints are documented
            paths = openapi_spec["paths"]
            assert "/orchestration/status/{workflow_id}" in paths
            assert "/orchestration/workflows" in paths
            
            # Check that models are documented
            components = openapi_spec.get("components", {})
            schemas = components.get("schemas", {})
            assert "WorkflowStatus" in schemas
            assert "AgentStatus" in schemas
            assert "WorkflowListItem" in schemas