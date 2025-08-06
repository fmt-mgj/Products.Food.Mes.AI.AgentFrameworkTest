"""Performance tests for parallel agent execution."""

import asyncio
import time
import pytest
from unittest.mock import Mock, patch, AsyncMock
from pathlib import Path

from generated.executor import FlowExecutor, RunRequest, ExecutionGroup
from generated.memory import MemoryManager


class MockAgent:
    """Mock agent that sleeps for a specified duration."""
    
    def __init__(self, sleep_duration: float = 1.0, max_retries: int = 3, wait: float = 0.5):
        self.sleep_duration = sleep_duration
        self.max_retries = max_retries
        self.wait = wait
    
    async def prep(self, shared):
        return {"agent_id": shared.get("agent_id", "unknown")}
    
    async def exec(self, prep_result):
        # Simulate work by sleeping
        await asyncio.sleep(self.sleep_duration)
        return f"Mock result from {prep_result.get('agent_id', 'unknown')}"
    
    async def post(self, shared, prep_result, exec_result):
        shared[f"result_{prep_result.get('agent_id', 'unknown')}"] = exec_result
        return "success"


@pytest.fixture
async def mock_memory_manager():
    """Create a mock memory manager."""
    memory_manager = Mock(spec=MemoryManager)
    memory_manager.get = AsyncMock(return_value=None)
    memory_manager.set = AsyncMock()
    memory_manager.flush = AsyncMock()
    return memory_manager


@pytest.fixture
def mock_executor(mock_memory_manager):
    """Create a FlowExecutor with mocked components."""
    executor = FlowExecutor(mock_memory_manager)
    
    # Mock the agent loading
    executor.agents = {
        "agent1": MockAgent,
        "agent2": MockAgent, 
        "agent3": MockAgent
    }
    
    # Mock metadata for parallel vs sequential testing
    executor.agents_metadata = {
        "agent1": {"id": "agent1", "parallel": True},
        "agent2": {"id": "agent2", "parallel": True},
        "agent3": {"id": "agent3", "parallel": True}
    }
    
    executor.runtime_config = {"on_missing_doc": "skip"}
    return executor


class TestParallelExecutionPerformance:
    """Test parallel execution performance improvements."""
    
    @pytest.mark.asyncio
    async def test_parallel_execution_faster_than_sequential(self, mock_executor):
        """Test that parallel execution is faster than sequential for same agents."""
        sleep_duration = 1.0
        
        # Create 3 agents that each sleep for 1 second
        mock_executor.agents = {
            "agent1": lambda **kwargs: MockAgent(sleep_duration),
            "agent2": lambda **kwargs: MockAgent(sleep_duration),
            "agent3": lambda **kwargs: MockAgent(sleep_duration)
        }
        
        shared = {
            "input": "test input",
            "story_id": "test_story", 
            "flow": "default",
            "memory_manager": mock_executor.memory_manager,
            "all_results": {}
        }
        
        # Test parallel execution (all agents marked as parallel)
        mock_executor.agents_metadata = {
            "agent1": {"parallel": True},
            "agent2": {"parallel": True}, 
            "agent3": {"parallel": True}
        }
        
        start_time = time.time()
        parallel_results, parallel_metrics = await mock_executor.execute_parallel_group(
            ["agent1", "agent2", "agent3"], shared
        )
        parallel_time = time.time() - start_time
        
        # Test sequential execution (agents marked as sequential)
        mock_executor.agents_metadata = {
            "agent1": {"parallel": False},
            "agent2": {"parallel": False},
            "agent3": {"parallel": False}
        }
        
        start_time = time.time()
        for agent_name in ["agent1", "agent2", "agent3"]:
            context_key = await mock_executor.init_memory_context(shared["story_id"], agent_name)
            agent_shared = {**shared, "memory_context": context_key, "agent_id": agent_name}
            await mock_executor._execute_single_agent(agent_name, agent_shared)
        sequential_time = time.time() - start_time
        
        # Parallel should be significantly faster (at least 2x for 3 agents)
        assert parallel_time < sequential_time / 2, (
            f"Parallel execution ({parallel_time:.2f}s) should be much faster than "
            f"sequential ({sequential_time:.2f}s)"
        )
        
        # Parallel should be close to single agent time (within 20% overhead)
        assert parallel_time < sleep_duration * 1.2, (
            f"Parallel execution ({parallel_time:.2f}s) should be close to single agent time ({sleep_duration}s)"
        )
        
        # All agents should have completed successfully  
        assert len(parallel_results) == 3
        for agent_name in ["agent1", "agent2", "agent3"]:
            assert agent_name in parallel_results
            assert "Mock result" in str(parallel_results[agent_name])
    
    @pytest.mark.asyncio
    async def test_identify_parallel_groups_correctly_groups_agents(self, mock_executor):
        """Test that parallel agents are correctly identified and grouped."""
        # Test case: sequential -> parallel -> sequential -> parallel
        mock_executor.agents_metadata = {
            "agent1": {"parallel": False},  # Sequential
            "agent2": {"parallel": True},   # Parallel group 1 start
            "agent3": {"parallel": True},   # Parallel group 1 continue
            "agent4": {"parallel": False},  # Sequential (breaks parallel group)
            "agent5": {"parallel": True},   # Parallel group 2 start
            "agent6": {"parallel": True}    # Parallel group 2 continue
        }
        
        executable_agents = ["agent1", "agent2", "agent3", "agent4", "agent5", "agent6"]
        groups = mock_executor.identify_parallel_groups(executable_agents)
        
        expected_groups = [
            ExecutionGroup(agents=["agent1"], is_parallel=False),
            ExecutionGroup(agents=["agent2", "agent3"], is_parallel=True),
            ExecutionGroup(agents=["agent4"], is_parallel=False),
            ExecutionGroup(agents=["agent5", "agent6"], is_parallel=True)
        ]
        
        assert len(groups) == 4
        for i, (actual, expected) in enumerate(zip(groups, expected_groups)):
            assert actual.agents == expected.agents, f"Group {i} agents mismatch"
            assert actual.is_parallel == expected.is_parallel, f"Group {i} parallel flag mismatch"
    
    @pytest.mark.asyncio 
    async def test_parallel_group_executes_concurrently(self, mock_executor):
        """Test that parallel group actually executes agents concurrently."""
        sleep_duration = 0.5
        
        mock_executor.agents = {
            "fast1": lambda **kwargs: MockAgent(sleep_duration),
            "fast2": lambda **kwargs: MockAgent(sleep_duration),
            "fast3": lambda **kwargs: MockAgent(sleep_duration)
        }
        
        shared = {
            "input": "test",
            "story_id": "concurrent_test",
            "all_results": {}
        }
        
        start_time = time.time()
        results, metrics = await mock_executor.execute_parallel_group(
            ["fast1", "fast2", "fast3"], shared
        )
        execution_time = time.time() - start_time
        
        # Should complete in roughly the time of one agent, not three
        assert execution_time < sleep_duration * 2, (
            f"Concurrent execution took {execution_time:.2f}s, expected < {sleep_duration * 2}s"
        )
        
        # All agents should complete successfully
        assert len(results) == 3
        for agent in ["fast1", "fast2", "fast3"]:
            assert agent in results
    
    @pytest.mark.asyncio
    async def test_error_in_one_agent_doesnt_crash_others(self, mock_executor):
        """Test that error in one parallel agent doesn't crash others in same group."""
        
        class FailingMockAgent(MockAgent):
            async def exec(self, prep_result):
                if prep_result.get("agent_id") == "failing_agent":
                    raise RuntimeError("Simulated failure")
                return await super().exec(prep_result)
        
        mock_executor.agents = {
            "good_agent1": lambda **kwargs: FailingMockAgent(0.1),
            "failing_agent": lambda **kwargs: FailingMockAgent(0.1),
            "good_agent2": lambda **kwargs: FailingMockAgent(0.1)
        }
        
        shared = {
            "input": "test",
            "story_id": "error_test", 
            "all_results": {}
        }
        
        # Execute parallel group with one failing agent
        results, metrics = await mock_executor.execute_parallel_group(
            ["good_agent1", "failing_agent", "good_agent2"], shared
        )
        
        # Should have results for all agents
        assert len(results) == 3
        
        # Good agents should succeed
        assert "Mock result" in str(results["good_agent1"])
        assert "Mock result" in str(results["good_agent2"])
        
        # Failing agent should have error message
        assert "Error:" in str(results["failing_agent"])
        assert "Simulated failure" in str(results["failing_agent"])
    
    @pytest.mark.asyncio
    async def test_memory_isolation_between_parallel_agents(self, mock_executor):
        """Test that parallel agents have isolated memory contexts."""
        
        mock_executor.agents = {
            "agent_a": lambda **kwargs: MockAgent(0.1),
            "agent_b": lambda **kwargs: MockAgent(0.1)
        }
        
        shared = {
            "input": "isolation_test",
            "story_id": "memory_test",
            "all_results": {}
        }
        
        # Track memory context calls
        context_calls = []
        original_init_memory = mock_executor.init_memory_context
        
        async def track_memory_init(story_id, agent_id):
            context_key = await original_init_memory(story_id, agent_id)
            context_calls.append((story_id, agent_id, context_key))
            return context_key
        
        mock_executor.init_memory_context = track_memory_init
        
        # Execute parallel group
        results, metrics = await mock_executor.execute_parallel_group(["agent_a", "agent_b"], shared)
        
        # Should have separate memory contexts for each agent
        assert len(context_calls) >= 2
        
        # Context keys should be unique per agent
        context_keys = [call[2] for call in context_calls]
        assert len(set(context_keys)) >= 2, "Each agent should have unique memory context"
        
        # Context keys should follow pattern: {agent_id}:{story_id}
        for story_id, agent_id, context_key in context_calls:
            if context_key:  # Skip any None values
                expected_key = f"{agent_id}:{story_id}"
                assert context_key == expected_key, f"Expected {expected_key}, got {context_key}"
    
    @pytest.mark.asyncio
    async def test_sequential_order_preserved_between_groups(self, mock_executor):
        """Test that execution order is preserved between parallel groups."""
        
        execution_log = []
        
        class LoggingMockAgent(MockAgent):
            def __init__(self, agent_name, sleep_duration=0.1, **kwargs):
                super().__init__(sleep_duration, **kwargs)
                self.agent_name = agent_name
            
            async def exec(self, prep_result):
                execution_log.append(f"start_{self.agent_name}")
                result = await super().exec(prep_result)
                execution_log.append(f"end_{self.agent_name}")
                return result
        
        mock_executor.agents = {
            "seq1": lambda **kwargs: LoggingMockAgent("seq1"),
            "par1": lambda **kwargs: LoggingMockAgent("par1"),  
            "par2": lambda **kwargs: LoggingMockAgent("par2"),
            "seq2": lambda **kwargs: LoggingMockAgent("seq2")
        }
        
        mock_executor.agents_metadata = {
            "seq1": {"parallel": False},
            "par1": {"parallel": True},
            "par2": {"parallel": True}, 
            "seq2": {"parallel": False}
        }
        
        # Execute through main execute method to test group ordering
        request = RunRequest(
            input="order_test",
            story_id="order_test_story", 
            flow="default"
        )
        
        await mock_executor.execute(request)
        
        # Check execution order
        # seq1 should start and end before any parallel agents
        seq1_start = execution_log.index("start_seq1")
        seq1_end = execution_log.index("end_seq1")
        
        par_starts = [i for i, entry in enumerate(execution_log) if entry.startswith("start_par")]
        
        # seq1 should complete before parallel agents start
        assert seq1_end < min(par_starts), "Sequential agent should complete before parallel group starts"
        
        # seq2 should start after parallel agents complete
        seq2_start = execution_log.index("start_seq2")
        par_ends = [i for i, entry in enumerate(execution_log) if entry.startswith("end_par")]
        
        assert seq2_start > max(par_ends), "Sequential agent should start after parallel group completes"
    
    @pytest.mark.asyncio
    async def test_python_310_compatibility_with_gather_fallback(self, mock_executor):
        """Test that gather fallback works when TaskGroup is not available."""
        
        # Mock TaskGroup to not be available (simulate Python 3.10)
        with patch('asyncio.TaskGroup', side_effect=AttributeError("No TaskGroup")):
            mock_executor.agents = {
                "agent1": lambda **kwargs: MockAgent(0.1),
                "agent2": lambda **kwargs: MockAgent(0.1)
            }
            
            shared = {
                "input": "fallback_test",
                "story_id": "fallback_story",
                "all_results": {}
            }
            
            # Should still work using gather fallback
            results, metrics = await mock_executor.execute_parallel_group(
                ["agent1", "agent2"], shared
            )
            
            assert len(results) == 2
            assert "agent1" in results
            assert "agent2" in results