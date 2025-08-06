"""Integration tests for parallel agent execution."""

import asyncio
import pytest
from pathlib import Path
import tempfile
import shutil
from unittest.mock import Mock, AsyncMock

from generated.executor import FlowExecutor, RunRequest
from generated.memory import MemoryManager


@pytest.fixture
async def temp_project_structure():
    """Create temporary project structure for testing."""
    temp_dir = Path(tempfile.mkdtemp())
    
    # Create directory structure
    (temp_dir / "bmad" / "agents").mkdir(parents=True)
    (temp_dir / "generated" / "agents").mkdir(parents=True)
    (temp_dir / "config").mkdir(parents=True)
    
    # Create test agent BMAD files
    agent1_content = """---
id: parallel_agent1
description: First parallel test agent
tools: []
memory_scope: isolated
wait_for:
  docs: []
  agents: []
parallel: true
---

You are parallel agent 1. Process the input and return result.
"""
    
    agent2_content = """---
id: parallel_agent2  
description: Second parallel test agent
tools: []
memory_scope: isolated
wait_for:
  docs: []
  agents: []
parallel: true
---

You are parallel agent 2. Process the input and return result.
"""
    
    agent3_content = """---
id: sequential_agent
description: Sequential test agent
tools: []
memory_scope: isolated
wait_for:
  docs: []
  agents: [parallel_agent1, parallel_agent2]
parallel: false
---

You are a sequential agent that depends on parallel agents.
"""
    
    (temp_dir / "bmad" / "agents" / "parallel_agent1.md").write_text(agent1_content)
    (temp_dir / "bmad" / "agents" / "parallel_agent2.md").write_text(agent2_content)
    (temp_dir / "bmad" / "agents" / "sequential_agent.md").write_text(agent3_content)
    
    # Create runtime config
    config_content = """on_missing_doc: skip
"""
    (temp_dir / "config" / "runtime.yaml").write_text(config_content)
    
    yield temp_dir
    
    # Cleanup
    shutil.rmtree(temp_dir)


class MockParallelAgent:
    """Mock agent for parallel execution testing."""
    
    def __init__(self, agent_id: str, sleep_time: float = 0.1, max_retries: int = 3, wait: float = 0.5):
        self.agent_id = agent_id
        self.sleep_time = sleep_time
        self.max_retries = max_retries
        self.wait = wait
    
    async def prep(self, shared):
        return {"agent_id": self.agent_id, "input": shared.get("input")}
    
    async def exec(self, prep_result):
        await asyncio.sleep(self.sleep_time)
        return f"Result from {self.agent_id}: processed '{prep_result.get('input', 'no input')}'"
    
    async def post(self, shared, prep_result, exec_result):
        # Store result in shared context
        shared[f"result_{self.agent_id}"] = exec_result
        return "success"


@pytest.fixture
async def mock_memory_manager():
    """Mock memory manager for testing."""
    manager = Mock(spec=MemoryManager)
    manager.get = AsyncMock(return_value=None)
    manager.set = AsyncMock()
    manager.flush = AsyncMock()
    return manager


class TestParallelExecutionIntegration:
    """Integration tests for parallel execution functionality."""
    
    @pytest.mark.asyncio
    async def test_full_parallel_execution_flow(self, temp_project_structure, mock_memory_manager):
        """Test complete parallel execution flow with real-like setup."""
        
        # Change to temp directory for testing
        import os
        original_cwd = os.getcwd()
        os.chdir(temp_project_structure)
        
        try:
            # Create executor with mocked components
            executor = FlowExecutor(mock_memory_manager)
            
            # Mock the agents with our test agents
            executor.agents = {
                "parallel_agent1": lambda **kwargs: MockParallelAgent("parallel_agent1", 0.1),
                "parallel_agent2": lambda **kwargs: MockParallelAgent("parallel_agent2", 0.1),
                "sequential_agent": lambda **kwargs: MockParallelAgent("sequential_agent", 0.1)
            }
            
            # The metadata should be loaded from the BMAD files we created
            # But let's also ensure it's correct
            expected_metadata = {
                "parallel_agent1": {"id": "parallel_agent1", "parallel": True, "wait_for": {"docs": [], "agents": []}},
                "parallel_agent2": {"id": "parallel_agent2", "parallel": True, "wait_for": {"docs": [], "agents": []}},
                "sequential_agent": {"id": "sequential_agent", "parallel": False, "wait_for": {"docs": [], "agents": ["parallel_agent1", "parallel_agent2"]}}
            }
            
            executor.agents_metadata = expected_metadata
            
            # Create execution request
            request = RunRequest(
                input="test parallel execution",
                story_id="integration_test",
                flow="default"
            )
            
            # Execute and measure time
            import time
            start_time = time.time()
            response = await executor.execute(request)
            execution_time = time.time() - start_time
            
            # Verify successful execution
            assert response.result is not None
            assert "parallel_agent1" in response.result
            assert "parallel_agent2" in response.result  
            assert "sequential_agent" in response.result
            
            # Execution should be relatively fast due to parallelism
            # (both parallel agents + sequential agent, but parallel ones run concurrently)
            assert execution_time < 0.5, f"Execution took too long: {execution_time}s"
            
        finally:
            os.chdir(original_cwd)
    
    @pytest.mark.asyncio
    async def test_parallel_group_identification(self, temp_project_structure, mock_memory_manager):
        """Test that parallel groups are correctly identified from metadata."""
        
        import os
        original_cwd = os.getcwd()
        os.chdir(temp_project_structure)
        
        try:
            executor = FlowExecutor(mock_memory_manager)
            
            # Set up test metadata with mixed parallel/sequential agents
            executor.agents_metadata = {
                "seq1": {"parallel": False},
                "par1": {"parallel": True},
                "par2": {"parallel": True},
                "seq2": {"parallel": False},
                "par3": {"parallel": True},
                "par4": {"parallel": True}
            }
            
            executable_agents = ["seq1", "par1", "par2", "seq2", "par3", "par4"]
            groups = executor.identify_parallel_groups(executable_agents)
            
            # Should create 4 groups:
            # 1. [seq1] - sequential
            # 2. [par1, par2] - parallel  
            # 3. [seq2] - sequential
            # 4. [par3, par4] - parallel
            
            assert len(groups) == 4
            
            # Check first group (sequential)
            assert groups[0].agents == ["seq1"]
            assert groups[0].is_parallel == False
            
            # Check second group (parallel)  
            assert groups[1].agents == ["par1", "par2"]
            assert groups[1].is_parallel == True
            
            # Check third group (sequential)
            assert groups[2].agents == ["seq2"] 
            assert groups[2].is_parallel == False
            
            # Check fourth group (parallel)
            assert groups[3].agents == ["par3", "par4"]
            assert groups[3].is_parallel == True
            
        finally:
            os.chdir(original_cwd)
    
    @pytest.mark.asyncio 
    async def test_memory_isolation_in_parallel_execution(self, temp_project_structure, mock_memory_manager):
        """Test that memory contexts remain isolated during parallel execution."""
        
        import os
        original_cwd = os.getcwd()
        os.chdir(temp_project_structure)
        
        try:
            executor = FlowExecutor(mock_memory_manager)
            
            # Track memory context creation calls
            memory_calls = []
            original_init = executor.init_memory_context
            
            async def track_memory_calls(story_id, agent_id):
                result = await original_init(story_id, agent_id)
                memory_calls.append((story_id, agent_id, result))
                return result
            
            executor.init_memory_context = track_memory_calls
            
            # Set up parallel agents
            executor.agents = {
                "par1": lambda **kwargs: MockParallelAgent("par1"),
                "par2": lambda **kwargs: MockParallelAgent("par2")
            }
            
            executor.agents_metadata = {
                "par1": {"parallel": True},
                "par2": {"parallel": True}
            }
            
            shared = {
                "input": "isolation_test",
                "story_id": "memory_isolation_test",
                "all_results": {}
            }
            
            # Execute parallel group
            results, metrics = await executor.execute_parallel_group(["par1", "par2"], shared)
            
            # Verify separate memory contexts were created
            par1_calls = [call for call in memory_calls if call[1] == "par1"]
            par2_calls = [call for call in memory_calls if call[1] == "par2"]
            
            assert len(par1_calls) >= 1, "par1 should have memory context"
            assert len(par2_calls) >= 1, "par2 should have memory context"
            
            # Context keys should be unique
            par1_context = par1_calls[0][2]
            par2_context = par2_calls[0][2] 
            
            assert par1_context != par2_context, "Parallel agents should have different memory contexts"
            assert "par1:memory_isolation_test" in par1_context
            assert "par2:memory_isolation_test" in par2_context
            
        finally:
            os.chdir(original_cwd)
    
    @pytest.mark.asyncio
    async def test_error_handling_in_parallel_group(self, mock_memory_manager):
        """Test error handling doesn't break parallel execution."""
        
        class ErrorAgent(MockParallelAgent):
            async def exec(self, prep_result):
                if self.agent_id == "error_agent":
                    raise ValueError("Test error")
                return await super().exec(prep_result)
        
        executor = FlowExecutor(mock_memory_manager)
        executor.agents = {
            "good_agent": lambda **kwargs: ErrorAgent("good_agent"),
            "error_agent": lambda **kwargs: ErrorAgent("error_agent")
        }
        
        shared = {
            "input": "error_test", 
            "story_id": "error_test_story",
            "all_results": {}
        }
        
        # Should not raise exception, should handle errors gracefully
        results, metrics = await executor.execute_parallel_group(
            ["good_agent", "error_agent"], shared
        )
        
        # Both agents should have results (error agent will have error message)
        assert len(results) == 2
        assert "good_agent" in results
        assert "error_agent" in results
        
        # Good agent should succeed
        assert "Result from good_agent" in str(results["good_agent"])
        
        # Error agent should have error in result
        assert "Error:" in str(results["error_agent"])
        assert "Test error" in str(results["error_agent"])