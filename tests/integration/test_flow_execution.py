"""Integration tests for flow execution endpoint."""

import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from pathlib import Path
import tempfile
import shutil

# Test the actual imports
from generated.executor import FlowExecutor, RunRequest, RunResponse
from generated.memory import MemoryManager
from pocketflow import AsyncNode, BaseNode


class MockTestAgent(AsyncNode):
    """Mock async agent for testing purposes."""
    
    async def prep_async(self, shared):
        return {"input": shared.get("input", "")}
    
    async def exec_async(self, prep_res):
        # Simple mock processing
        return {"output": f"processed: {prep_res['input']}"}
    
    async def post_async(self, shared, prep_res, exec_res):
        shared["test_agent_result"] = exec_res["output"]
        shared["final_result"] = exec_res["output"]
        return "complete"


class MockFailingAgent(AsyncNode):
    """Mock async agent that always fails for error testing."""
    
    async def prep_async(self, shared):
        return {"input": shared.get("input", "")}
    
    async def exec_async(self, prep_res):
        raise Exception("Mock agent failure")
    
    async def post_async(self, shared, prep_res, exec_res):
        return "complete"


@pytest.fixture
def temp_memory_dir():
    """Create temporary memory directory."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def flow_executor_with_mock_agents(temp_memory_dir):
    """Create FlowExecutor with mock agents for testing."""
    memory_manager = MemoryManager(memory_dir=temp_memory_dir)
    executor = FlowExecutor(memory_manager)
    
    # Replace agents with mock agents
    executor.agents = {"test_agent": MockTestAgent}
    
    return executor


@pytest.mark.asyncio
async def test_run_flow_success(flow_executor_with_mock_agents):
    """Test successful flow execution."""
    request = RunRequest(
        flow="default",
        input="test input",
        story_id="test_story_001"
    )
    
    response = await flow_executor_with_mock_agents.execute(request)
    
    assert response.result == "processed: test input"
    assert response.pending_docs is None


@pytest.mark.asyncio
async def test_run_flow_missing_documents(flow_executor_with_mock_agents):
    """Test flow execution with missing documents."""
    # Mock document checker to return missing docs
    with patch.object(flow_executor_with_mock_agents, 'check_documents', new_callable=AsyncMock) as mock_check:
        mock_check.return_value = ["missing_doc1", "missing_doc2"]
        
        request = RunRequest(
            flow="default",
            input="test input", 
            story_id="test_story_001"
        )
        
        response = await flow_executor_with_mock_agents.execute(request)
        
        assert response.result is None
        assert response.pending_docs == ["missing_doc1", "missing_doc2"]


@pytest.mark.asyncio
async def test_run_flow_agent_error(temp_memory_dir):
    """Test error handling during agent execution."""
    memory_manager = MemoryManager(memory_dir=temp_memory_dir)
    executor = FlowExecutor(memory_manager)
    executor.agents = {"failing_agent": MockFailingAgent}
    
    request = RunRequest(
        flow="default",
        input="test input",
        story_id="test_story_001"
    )
    
    with pytest.raises(Exception) as exc_info:
        await executor.execute(request)
    
    assert "Mock agent failure" in str(exc_info.value)


@pytest.mark.asyncio
async def test_memory_isolation(flow_executor_with_mock_agents):
    """Test memory isolation between different story_ids."""
    # Execute flow with first story ID
    request1 = RunRequest(
        flow="default",
        input="story 1 input",
        story_id="story_001"
    )
    response1 = await flow_executor_with_mock_agents.execute(request1)
    
    # Execute flow with second story ID
    request2 = RunRequest(
        flow="default", 
        input="story 2 input",
        story_id="story_002"
    )
    response2 = await flow_executor_with_mock_agents.execute(request2)
    
    # Results should be different based on input
    assert response1.result == "processed: story 1 input"
    assert response2.result == "processed: story 2 input"


@pytest.mark.asyncio
async def test_concurrent_execution(flow_executor_with_mock_agents):
    """Test concurrent flow executions don't interfere."""
    # Execute multiple flows concurrently
    tasks = []
    for i in range(5):
        request = RunRequest(
            flow="default",
            input=f"concurrent input {i}",
            story_id=f"story_{i:03d}"
        )
        tasks.append(flow_executor_with_mock_agents.execute(request))
    
    responses = await asyncio.gather(*tasks)
    
    # All should succeed
    for i, response in enumerate(responses):
        assert response.result == f"processed: concurrent input {i}"
        assert response.pending_docs is None


@pytest.mark.asyncio 
async def test_document_dependency_checking():
    """Test document dependency checking functionality."""
    temp_dir = tempfile.mkdtemp()
    try:
        # Create temporary docs directory
        docs_dir = Path(temp_dir) / "docs"
        docs_dir.mkdir()
        
        # Create one document but not the other
        (docs_dir / "existing_doc.md").write_text("Content")
        
        memory_manager = MemoryManager(memory_dir=temp_dir)
        executor = FlowExecutor(memory_manager)
        
        # Mock the DOCS_DIR to point to our temp directory
        with patch('generated.executor.DOCS_DIR', docs_dir):
            missing = await executor.check_documents(["existing_doc", "missing_doc"])
            assert missing == ["missing_doc"]
            
            missing = await executor.check_documents(["existing_doc"])
            assert missing == []
            
    finally:
        shutil.rmtree(temp_dir)


@pytest.mark.asyncio
async def test_memory_context_initialization():
    """Test memory context initialization."""
    temp_dir = tempfile.mkdtemp()
    try:
        memory_manager = MemoryManager(memory_dir=temp_dir)
        executor = FlowExecutor(memory_manager)
        
        # Initialize context
        context_key = await executor.init_memory_context("story_123", "test_agent")
        assert context_key == "test_agent:story_123"
        
        # Verify context was created
        context = await memory_manager.get("isolated", context_key)
        assert context["story_id"] == "story_123"
        assert context["agent_id"] == "test_agent"
        assert context["status"] == "initialized"
        
        # Test idempotency - initializing again should not overwrite
        await executor.init_memory_context("story_123", "test_agent")
        context2 = await memory_manager.get("isolated", context_key)
        assert context2 == context
        
    finally:
        shutil.rmtree(temp_dir)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])