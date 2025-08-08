import asyncio
import json
import tempfile
from datetime import datetime, timezone, timedelta
from pathlib import Path

import httpx
import pytest
from httpx import ASGITransport

from generated.app import app
from generated.models import HistoryEntry, WorkflowStatus, AgentStatus


@pytest.fixture
async def client():
    """Create async HTTP client."""
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client


@pytest.fixture
def temp_storage_dir():
    """Create temporary storage directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Set up the storage directories
        history_dir = Path(tmpdir) / "history"
        shared_dir = Path(tmpdir) / "shared"
        history_dir.mkdir()
        shared_dir.mkdir()
        
        # Update services to use temp directory
        from generated.app import history_service, status_service
        history_service.storage_dir = history_dir
        history_service.agent_index_dir = history_dir / "agent_index"
        history_service.agent_index_dir.mkdir()
        status_service.storage_dir = shared_dir
        
        yield tmpdir


class TestHistoryService:
    """Unit tests for HistoryService."""
    
    async def test_append_history_creates_file(self, temp_storage_dir):
        """Test that appending history creates the JSONL file."""
        from generated.history_service import HistoryService
        
        service = HistoryService(str(Path(temp_storage_dir) / "history"))
        
        entry = HistoryEntry(
            workflow_id="test-workflow",
            story_id="6.2",
            agent_id="parser",
            status="completed",
            execution_duration_ms=1000,
            output_summary="Test completion"
        )
        
        await service.append_history(entry)
        
        # Check file was created
        history_file = service._get_history_file_path("test-workflow")
        assert history_file.exists()
        
        # Check content
        with open(history_file) as f:
            line = f.readline().strip()
            data = json.loads(line)
            assert data["workflow_id"] == "test-workflow"
            assert data["status"] == "completed"


    async def test_append_history_is_thread_safe(self, temp_storage_dir):
        """Test that append operations are thread-safe."""
        import asyncio
        from generated.history_service import HistoryService
        
        service = HistoryService(str(Path(temp_storage_dir) / "history"))
        
        # Create multiple entries to append simultaneously
        entries = []
        for i in range(10):
            entry = HistoryEntry(
                workflow_id="test-workflow",
                story_id="6.2", 
                agent_id=f"agent-{i}",
                status="completed",
                execution_duration_ms=i * 100
            )
            entries.append(entry)
        
        # Append all entries concurrently
        await asyncio.gather(*[service.append_history(entry) for entry in entries])
        
        # Check all entries were written
        history_file = service._get_history_file_path("test-workflow")
        with open(history_file) as f:
            lines = f.readlines()
            assert len(lines) == 10


    async def test_get_workflow_history_returns_all_entries(self, temp_storage_dir):
        """Test that get_workflow_history returns all entries."""
        from generated.history_service import HistoryService
        
        service = HistoryService(str(Path(temp_storage_dir) / "history"))
        
        # Create test entries
        entries = []
        for i in range(5):
            entry = HistoryEntry(
                workflow_id="test-workflow",
                story_id="6.2",
                agent_id=f"agent-{i}",
                status="completed",
                execution_duration_ms=i * 100
            )
            entries.append(entry)
            await service.append_history(entry)
        
        # Get all entries
        retrieved = await service.get_workflow_history("test-workflow")
        
        assert len(retrieved) == 5
        # Should be sorted newest first
        assert retrieved[0].agent_id == "agent-4"


    async def test_get_workflow_history_with_time_filter(self, temp_storage_dir):
        """Test workflow history with time range filtering."""
        from generated.history_service import HistoryService
        import asyncio
        
        service = HistoryService(str(Path(temp_storage_dir) / "history"))
        
        # Create entries with different timestamps
        base_time = datetime.now(timezone.utc)
        
        entry1 = HistoryEntry(
            workflow_id="test-workflow",
            story_id="6.2",
            agent_id="agent-1", 
            status="completed",
            timestamp=base_time
        )
        
        entry2 = HistoryEntry(
            workflow_id="test-workflow",
            story_id="6.2",
            agent_id="agent-2",
            status="completed",
            timestamp=base_time + timedelta(hours=1)
        )
        
        await service.append_history(entry1)
        await asyncio.sleep(0.01)  # Ensure different timestamps
        await service.append_history(entry2)
        
        # Filter by start time
        filtered = await service.get_workflow_history(
            "test-workflow",
            start_time=base_time + timedelta(minutes=30)
        )
        
        assert len(filtered) == 1
        assert filtered[0].agent_id == "agent-2"


    async def test_get_workflow_history_pagination(self, temp_storage_dir):
        """Test workflow history pagination."""
        from generated.history_service import HistoryService
        
        service = HistoryService(str(Path(temp_storage_dir) / "history"))
        
        # Create 10 test entries
        for i in range(10):
            entry = HistoryEntry(
                workflow_id="test-workflow",
                story_id="6.2",
                agent_id=f"agent-{i:02d}",
                status="completed"
            )
            await service.append_history(entry)
        
        # Test pagination
        page1 = await service.get_workflow_history("test-workflow", limit=3, offset=0)
        page2 = await service.get_workflow_history("test-workflow", limit=3, offset=3)
        
        assert len(page1) == 3
        assert len(page2) == 3
        assert page1[0].agent_id != page2[0].agent_id


    async def test_get_agent_history_across_workflows(self, temp_storage_dir):
        """Test getting agent history across multiple workflows."""
        from generated.history_service import HistoryService
        
        service = HistoryService(str(Path(temp_storage_dir) / "history"))
        
        # Create entries for same agent in different workflows
        entry1 = HistoryEntry(
            workflow_id="workflow-1",
            story_id="6.1",
            agent_id="parser",
            status="completed"
        )
        
        entry2 = HistoryEntry(
            workflow_id="workflow-2", 
            story_id="6.2",
            agent_id="parser",
            status="failed"
        )
        
        await service.append_history(entry1)
        await service.append_history(entry2)
        
        # Get agent history across workflows
        agent_history = await service.get_agent_history("parser")
        
        assert len(agent_history) == 2
        workflow_ids = {entry.workflow_id for entry in agent_history}
        assert workflow_ids == {"workflow-1", "workflow-2"}


class TestHistoryEndpoints:
    """Integration tests for history API endpoints."""

    async def test_get_workflow_history_endpoint(self, client, temp_storage_dir):
        """Test GET /orchestration/history/{workflow_id} endpoint."""
        from generated.app import history_service
        
        # Create test data
        entry = HistoryEntry(
            workflow_id="test-workflow",
            story_id="6.2",
            agent_id="parser",
            status="completed",
            execution_duration_ms=2000,
            output_summary="Successfully parsed"
        )
        await history_service.append_history(entry)
        
        # Test endpoint
        response = await client.get("/orchestration/history/test-workflow")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["workflow_id"] == "test-workflow"
        assert data[0]["agent_id"] == "parser"
        assert data[0]["status"] == "completed"


    async def test_get_workflow_history_with_filters(self, client, temp_storage_dir):
        """Test workflow history endpoint with query parameters."""
        from generated.app import history_service
        
        # Create test data
        base_time = datetime.now(timezone.utc)
        
        entry1 = HistoryEntry(
            workflow_id="test-workflow",
            story_id="6.2", 
            agent_id="parser",
            status="running",
            timestamp=base_time
        )
        
        entry2 = HistoryEntry(
            workflow_id="test-workflow",
            story_id="6.2",
            agent_id="generator", 
            status="completed",
            timestamp=base_time + timedelta(hours=1)
        )
        
        await history_service.append_history(entry1)
        await history_service.append_history(entry2)
        
        # Test with pagination
        response = await client.get("/orchestration/history/test-workflow?limit=1")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1


    async def test_get_agent_history_endpoint(self, client, temp_storage_dir):
        """Test GET /orchestration/history/agent/{agent_id} endpoint."""
        from generated.app import history_service
        
        # Create test data for same agent in different workflows
        entry1 = HistoryEntry(
            workflow_id="workflow-1",
            story_id="6.1",
            agent_id="parser",
            status="completed"
        )
        
        entry2 = HistoryEntry(
            workflow_id="workflow-2",
            story_id="6.2", 
            agent_id="parser",
            status="running"
        )
        
        await history_service.append_history(entry1)
        await history_service.append_history(entry2)
        
        # Test endpoint
        response = await client.get("/orchestration/history/agent/parser")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        
        # Check both workflows are represented
        workflow_ids = {entry["workflow_id"] for entry in data}
        assert workflow_ids == {"workflow-1", "workflow-2"}


    async def test_history_entry_validation(self, temp_storage_dir):
        """Test that HistoryEntry model validation works correctly."""
        from generated.models import HistoryEntry
        from pydantic import ValidationError
        
        # Test valid entry
        entry = HistoryEntry(
            workflow_id="valid-workflow",
            story_id="6.2",
            agent_id="parser",
            status="completed"
        )
        assert entry.workflow_id == "valid-workflow"
        
        # Test invalid workflow_id (path traversal)
        with pytest.raises(ValidationError):
            HistoryEntry(
                workflow_id="../../../etc/passwd",
                story_id="6.2",
                agent_id="parser", 
                status="completed"
            )
        
        # Test invalid status
        with pytest.raises(ValidationError):
            HistoryEntry(
                workflow_id="valid-workflow",
                story_id="6.2", 
                agent_id="parser",
                status="invalid-status"
            )


    async def test_execution_duration_calculation(self, temp_storage_dir):
        """Test that execution duration is calculated correctly."""
        base_time = datetime.now(timezone.utc)
        start_time = base_time
        end_time = base_time + timedelta(seconds=30)  # 30 seconds later
        
        entry = HistoryEntry(
            workflow_id="test-workflow",
            story_id="6.2",
            agent_id="parser",
            status="completed",
            start_time=start_time,
            end_time=end_time
        )
        
        # Should automatically calculate duration
        assert entry.execution_duration_ms == 30000  # 30 seconds = 30000 ms


    async def test_status_update_creates_history(self, client, temp_storage_dir):
        """Test that status updates create history entries."""
        from generated.app import status_service, history_service
        
        # Create a workflow status
        workflow_status = WorkflowStatus(
            workflow_id="test-workflow",
            story_id="6.2",
            agent_statuses={
                "parser": AgentStatus(status="completed", output_summary="Parsed successfully")
            }
        )
        
        # Write status (should trigger history creation)
        await status_service.write_status(workflow_status)
        
        # Check that history was created
        history = await history_service.get_workflow_history("test-workflow")
        
        assert len(history) == 1
        assert history[0].agent_id == "parser"
        assert history[0].status == "completed"
        assert history[0].output_summary == "Parsed successfully"


    async def test_history_files_are_append_only(self, temp_storage_dir):
        """Test that history files are truly append-only."""
        from generated.history_service import HistoryService
        
        service = HistoryService(str(Path(temp_storage_dir) / "history"))
        
        # Append first entry
        entry1 = HistoryEntry(
            workflow_id="test-workflow",
            story_id="6.2",
            agent_id="parser",
            status="running"
        )
        await service.append_history(entry1)
        
        # Append second entry
        entry2 = HistoryEntry(
            workflow_id="test-workflow",
            story_id="6.2",
            agent_id="parser", 
            status="completed"
        )
        await service.append_history(entry2)
        
        # Check both entries exist (not overwritten)
        history = await service.get_workflow_history("test-workflow")
        assert len(history) == 2
        
        # Check they're in the file
        history_file = service._get_history_file_path("test-workflow")
        with open(history_file) as f:
            lines = f.readlines()
            assert len(lines) == 2


    async def test_no_analysis_logic_in_history(self, client, temp_storage_dir):
        """Test that no analysis or aggregation is performed in history endpoints."""
        from generated.app import history_service
        
        # Create entries with various statuses and durations
        entries = [
            HistoryEntry(
                workflow_id="test-workflow",
                story_id="6.2",
                agent_id="agent1",
                status="completed", 
                execution_duration_ms=1000
            ),
            HistoryEntry(
                workflow_id="test-workflow",
                story_id="6.2",
                agent_id="agent1",
                status="failed",
                execution_duration_ms=500
            )
        ]
        
        for entry in entries:
            await history_service.append_history(entry)
        
        # Get raw history
        response = await client.get("/orchestration/history/test-workflow")
        data = response.json()
        
        # Should return raw entries, no aggregation
        assert len(data) == 2
        
        # Check that raw fields are present (no computed fields)
        for entry in data:
            assert "workflow_id" in entry
            assert "agent_id" in entry
            assert "status" in entry
            assert "execution_duration_ms" in entry
            
            # No analysis fields should be present
            assert "average_duration" not in entry
            assert "success_rate" not in entry
            assert "total_executions" not in entry