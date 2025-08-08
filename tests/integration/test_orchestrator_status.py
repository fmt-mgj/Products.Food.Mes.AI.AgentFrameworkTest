import asyncio
import json
import tempfile
from datetime import datetime
from pathlib import Path

import httpx
import pytest
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
            story_id="test-story",
            agent_statuses={"agent1": AgentStatus(status="running")}
        )
        await status_service_with_temp_storage.write_status(initial_status)

        # Update status
        updated_status = WorkflowStatus(
            workflow_id=workflow_id,
            story_id="test-story",
            agent_statuses={"agent1": AgentStatus(status="completed", output_summary="Done")}
        )
        await status_service_with_temp_storage.write_status(updated_status)

        # Read status should return latest
        result = await status_service_with_temp_storage.read_status(workflow_id)
        assert result is not None
        assert result.agent_statuses["agent1"].status == "completed"
        assert result.agent_statuses["agent1"].output_summary == "Done"

    @pytest.mark.asyncio
    async def test_get_status_not_found_returns_404(self):
        """Test that GET status for non-existent workflow returns 404."""
        transport = ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/orchestration/status/non-existent-workflow")
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
                "story_id": "test-story",
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
            "story_id": "test-story",
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
                "story_id": "test-story",
                "agent_statuses": {"agent1": {"status": "pending"}}
            }
            await ac.put(f"/orchestration/status/{workflow_id}", json=initial_status)

            # Update status
            updated_status = {
                "workflow_id": workflow_id,
                "story_id": "test-story",
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
            "story_id": "test-story",
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
                    "story_id": "test-story",
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
                    "story_id": "test-story",
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
            "story_id": "test-story",
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
            WorkflowStatus(workflow_id=workflow_id, story_id="test-story", agent_statuses={"agent1": AgentStatus(status="pending")}),
            WorkflowStatus(workflow_id=workflow_id, story_id="test-story", agent_statuses={"agent1": AgentStatus(status="running")}),
            WorkflowStatus(workflow_id=workflow_id, story_id="test-story", agent_statuses={"agent1": AgentStatus(status="completed")})
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
                    "story_id": "test-story",
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


class TestStory61QueryBasedEndpoints:
    """Test Story 6.1 query-based endpoints with story_id support."""

    @pytest.mark.asyncio
    async def test_get_status_with_workflow_filter(self):
        """Test GET /orchestration/status?workflow_id=xxx filtering."""
        transport = ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
            # Create test workflows
            workflows = [
                {
                    "workflow_id": "wf-1",
                    "story_id": "5.1",
                    "agent_statuses": {"agent1": {"status": "completed"}}
                },
                {
                    "workflow_id": "wf-2",
                    "story_id": "5.2",
                    "agent_statuses": {"agent2": {"status": "pending"}}
                }
            ]

            for workflow in workflows:
                await ac.put("/orchestration/status", json=workflow)

            # Test single workflow filter
            response = await ac.get("/orchestration/status?workflow_id=wf-1")
            assert response.status_code == 200

            data = response.json()
            assert len(data) == 1
            assert data[0]["workflow_id"] == "wf-1"
            assert data[0]["story_id"] == "5.1"

    @pytest.mark.asyncio
    async def test_get_status_with_story_filter(self):
        """Test GET /orchestration/status?story_id=xxx filtering."""
        transport = ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
            # Create test workflows
            workflows = [
                {
                    "workflow_id": "story-wf-1",
                    "story_id": "5.1",
                    "agent_statuses": {"agent1": {"status": "completed"}}
                },
                {
                    "workflow_id": "story-wf-2",
                    "story_id": "5.1",
                    "agent_statuses": {"agent2": {"status": "pending"}}
                },
                {
                    "workflow_id": "story-wf-3",
                    "story_id": "5.2",
                    "agent_statuses": {"agent3": {"status": "running"}}
                }
            ]

            for workflow in workflows:
                await ac.put("/orchestration/status", json=workflow)

            # Test story filter
            response = await ac.get("/orchestration/status?story_id=5.1")
            assert response.status_code == 200

            data = response.json()
            assert len(data) == 2
            for item in data:
                assert item["story_id"] == "5.1"

    @pytest.mark.asyncio
    async def test_get_status_with_combined_filters(self):
        """Test GET /orchestration/status with both workflow_id and story_id."""
        transport = ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
            # Create test workflow
            workflow = {
                "workflow_id": "combined-test",
                "story_id": "5.1",
                "agent_statuses": {"agent1": {"status": "completed"}}
            }
            await ac.put("/orchestration/status", json=workflow)

            # Should find matching workflow
            response = await ac.get("/orchestration/status?workflow_id=combined-test&story_id=5.1")
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 1
            assert data[0]["workflow_id"] == "combined-test"
            assert data[0]["story_id"] == "5.1"

            # Should not find with wrong story_id
            response = await ac.get("/orchestration/status?workflow_id=combined-test&story_id=5.2")
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 0

    @pytest.mark.asyncio
    async def test_get_status_pagination(self):
        """Test GET /orchestration/status with pagination."""
        transport = ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
            # Create multiple workflows
            for i in range(5):
                workflow = {
                    "workflow_id": f"page-wf-{i}",
                    "story_id": "6.1",
                    "agent_statuses": {"agent1": {"status": "pending"}}
                }
                await ac.put("/orchestration/status", json=workflow)

            # Test limit parameter
            response = await ac.get("/orchestration/status?story_id=6.1&limit=3")
            assert response.status_code == 200
            data = response.json()
            assert len(data) <= 3

    @pytest.mark.asyncio
    async def test_put_status_creates_new(self):
        """Test PUT /orchestration/status creates new workflow."""
        transport = ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
            workflow_status = {
                "workflow_id": "new-put-test",
                "story_id": "6.1",
                "agent_statuses": {
                    "validator": {"status": "pending"}
                }
            }

            response = await ac.put("/orchestration/status", json=workflow_status)
            assert response.status_code == 200

            data = response.json()
            assert data["workflow_id"] == "new-put-test"
            assert data["story_id"] == "6.1"
            assert data["agent_statuses"]["validator"]["status"] == "pending"

    @pytest.mark.asyncio
    async def test_put_status_updates_existing(self):
        """Test PUT /orchestration/status updates existing workflow."""
        transport = ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
            # Create initial
            initial = {
                "workflow_id": "update-put-test",
                "story_id": "6.1",
                "agent_statuses": {"agent1": {"status": "pending"}}
            }
            await ac.put("/orchestration/status", json=initial)

            # Update
            updated = {
                "workflow_id": "update-put-test",
                "story_id": "6.1",
                "agent_statuses": {"agent1": {"status": "completed", "output_summary": "Updated"}}
            }

            response = await ac.put("/orchestration/status", json=updated)
            assert response.status_code == 200

            # Verify update
            get_response = await ac.get("/orchestration/status?workflow_id=update-put-test")
            data = get_response.json()
            assert data[0]["agent_statuses"]["agent1"]["status"] == "completed"

    @pytest.mark.asyncio
    async def test_story_id_validation(self):
        """Test story_id validation."""
        transport = ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
            # Valid story_id formats
            valid_ids = ["5.1", "5.2", "story-1", "story_1", "6.1.1"]
            for story_id in valid_ids:
                workflow = {
                    "workflow_id": f"test-{story_id.replace('.', '-')}",
                    "story_id": story_id,
                    "agent_statuses": {"agent1": {"status": "pending"}}
                }
                response = await ac.put("/orchestration/status", json=workflow)
                assert response.status_code == 200, f"Valid story_id {story_id} was rejected"

            # Invalid story_id formats
            invalid_ids = ["../test", "test/sub", "test\\sub"]
            for story_id in invalid_ids:
                workflow = {
                    "workflow_id": "invalid-test",
                    "story_id": story_id,
                    "agent_statuses": {"agent1": {"status": "pending"}}
                }
                response = await ac.put("/orchestration/status", json=workflow)
                assert response.status_code == 422, f"Invalid story_id {story_id} was accepted"

    @pytest.mark.asyncio
    async def test_get_workflows_active_endpoint(self):
        """Test GET /orchestration/workflows/active endpoint."""
        transport = ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
            # Create active workflow
            workflow = {
                "workflow_id": "active-test",
                "story_id": "6.1",
                "agent_statuses": {"agent1": {"status": "running"}}
            }
            await ac.put("/orchestration/status", json=workflow)

            # Get active workflows
            response = await ac.get("/orchestration/workflows/active")
            assert response.status_code == 200

            data = response.json()
            assert len(data) >= 1

            # Should be WorkflowStatus objects, not WorkflowListItem
            active_workflow = next((w for w in data if w["workflow_id"] == "active-test"), None)
            assert active_workflow is not None
            assert active_workflow["story_id"] == "6.1"
            assert "agent_statuses" in active_workflow

    @pytest.mark.asyncio
    async def test_backward_compatibility_with_5_3(self):
        """Test backward compatibility with Story 5.3 endpoints."""
        transport = ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
            # Old format without story_id should now work with new endpoint
            # due to default story_id value
            old_workflow = {
                "workflow_id": "legacy-test",
                "agent_statuses": {"agent1": {"status": "completed"}}
            }

            # This should now succeed because story_id has default value
            response = await ac.put("/orchestration/status", json=old_workflow)
            assert response.status_code == 200
            
            # Verify story_id was set to default "unknown"
            data = response.json()
            assert data["story_id"] == "unknown"

            # Legacy endpoint should also still work
            old_workflow_with_story = {
                "workflow_id": "legacy-test-2",
                "story_id": "unknown",
                "agent_statuses": {"agent1": {"status": "completed"}}
            }
            response = await ac.put("/orchestration/status/legacy-test-2", json=old_workflow_with_story)
            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_concurrent_workflow_updates(self):
        """Test concurrent updates don't interfere."""
        transport = ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
            async def update_workflow(workflow_id: str, story_id: str):
                workflow = {
                    "workflow_id": workflow_id,
                    "story_id": story_id,
                    "agent_statuses": {"agent1": {"status": "running"}}
                }
                return await ac.put("/orchestration/status", json=workflow)

            # Run concurrent updates
            tasks = [
                update_workflow("concurrent-new-1", "6.1"),
                update_workflow("concurrent-new-2", "6.1"),
                update_workflow("concurrent-new-3", "6.2")
            ]

            results = await asyncio.gather(*tasks)

            # All should succeed
            for result in results:
                assert result.status_code == 200

    @pytest.mark.asyncio
    async def test_no_business_logic_in_orchestrator(self):
        """Test that orchestrator contains no business logic."""
        transport = ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
            # Create workflow with failed status
            workflow = {
                "workflow_id": "no-logic-test",
                "story_id": "6.1",
                "agent_statuses": {"agent1": {"status": "failed"}}
            }
            await ac.put("/orchestration/status", json=workflow)

            # Orchestrator should store the failed status without trying to fix it
            response = await ac.get("/orchestration/status?workflow_id=no-logic-test")
            data = response.json()
            assert data[0]["agent_statuses"]["agent1"]["status"] == "failed"

            # Update to completed - should work without any dependency checking
            updated = {
                "workflow_id": "no-logic-test",
                "story_id": "6.1",
                "agent_statuses": {"agent2": {"status": "completed"}}  # Different agent!
            }
            response = await ac.put("/orchestration/status", json=updated)
            assert response.status_code == 200  # Should succeed with no validation

    @pytest.mark.asyncio
    async def test_cleanup_old_workflows_functionality(self, status_service_with_temp_storage):
        """Test cleanup_old_workflows removes old workflows."""
        import asyncio
        from datetime import datetime, timezone, timedelta
        from pathlib import Path
        import os
        
        # Create some test workflows
        old_workflow = WorkflowStatus(
            workflow_id="old-workflow",
            story_id="6.1",
            agent_statuses={"agent1": AgentStatus(status="completed")}
        )
        new_workflow = WorkflowStatus(
            workflow_id="new-workflow", 
            story_id="6.1",
            agent_statuses={"agent1": AgentStatus(status="running")}
        )
        
        # Write both workflows
        await status_service_with_temp_storage.write_status(old_workflow)
        await status_service_with_temp_storage.write_status(new_workflow)
        
        # Manually set old file modification time to simulate old workflow
        old_file_path = status_service_with_temp_storage._get_status_file_path("old-workflow")
        old_time = (datetime.now() - timedelta(days=10)).timestamp()
        os.utime(old_file_path, (old_time, old_time))
        
        # Verify both files exist
        assert old_file_path.exists()
        new_file_path = status_service_with_temp_storage._get_status_file_path("new-workflow")
        assert new_file_path.exists()
        
        # Run cleanup with 7 days retention
        cleaned_count = await status_service_with_temp_storage.cleanup_old_workflows(retention_days=7)
        
        # Old file should be cleaned, new file should remain
        assert cleaned_count == 1
        assert not old_file_path.exists()
        assert new_file_path.exists()
        
        # Should still be able to read the new workflow
        status = await status_service_with_temp_storage.read_status("new-workflow")
        assert status is not None
        assert status.workflow_id == "new-workflow"


class TestOpenAPIDocumentation:
    """Test OpenAPI documentation generation."""

    @pytest.mark.asyncio
    async def test_openapi_documentation_generated(self):
        """Test that OpenAPI docs are properly generated."""
        transport = ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/openapi.json")
            assert response.status_code == 200

            openapi_spec = response.json()

            # Check that our endpoints are documented
            paths = openapi_spec["paths"]
            assert "/orchestration/status/{workflow_id}" in paths
            assert "/orchestration/status" in paths  # New query-based endpoint
            assert "/orchestration/workflows" in paths
            assert "/orchestration/workflows/active" in paths  # New active endpoint

            # Check that models are documented
            components = openapi_spec.get("components", {})
            schemas = components.get("schemas", {})
            assert "WorkflowStatus" in schemas
            assert "AgentStatus" in schemas
            assert "WorkflowListItem" in schemas

    @pytest.mark.asyncio
    async def test_docs_accessible(self):
        """Test that /docs endpoint is accessible."""
        transport = ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/docs")
            assert response.status_code == 200
            # Should contain HTML with Swagger UI
            content = response.text
            assert "swagger" in content.lower() or "openapi" in content.lower()
