"""Tests to ensure backward compatibility with existing stateful agents."""

import pytest
from unittest.mock import patch, Mock

from generated.agents.analyst import AnalystNode
from generated.agents.summarizer import SummarizerNode
from generated.app import load_agent_class, AgentNotFoundError


class TestBackwardCompatibility:
    """Ensure existing stateful agents continue to work alongside new stateless agents."""
    
    @patch('utils.call_llm')
    def test_existing_analyst_node_still_works(self, mock_llm):
        """Test that existing AnalystNode continues to function."""
        mock_llm.return_value = "Analysis complete: Found 3 key trends in the data."
        
        agent = AnalystNode()
        shared = {"input": "Sample data for analysis"}
        
        # Test the full Node lifecycle
        result = agent.run(shared)
        
        # Verify it still follows the old pattern
        assert result == "default"  # Returns action string
        assert shared["analyst_result"] == "Analysis complete: Found 3 key trends in the data."
        assert shared["last_result"] == "Analysis complete: Found 3 key trends in the data."
        
        # Verify LLM was called with expected prompt structure
        mock_llm.assert_called_once()
        call_args = mock_llm.call_args[0][0]
        assert "data analyst agent" in call_args.lower()
        assert "Sample data for analysis" in call_args
    
    @patch('utils.call_llm')
    def test_existing_summarizer_node_still_works(self, mock_llm):
        """Test that existing SummarizerNode continues to function."""
        mock_llm.return_value = "Executive Summary: Key findings indicate strong performance."
        
        agent = SummarizerNode()
        shared = {"input": "Previous analysis results to summarize"}
        
        result = agent.run(shared)
        
        assert result == "default"
        assert shared["summarizer_result"] == "Executive Summary: Key findings indicate strong performance."
        assert shared["last_result"] == "Executive Summary: Key findings indicate strong performance."
        
        mock_llm.assert_called_once()
        call_args = mock_llm.call_args[0][0]
        assert "summarization agent" in call_args.lower()
        assert "Previous analysis results to summarize" in call_args
    
    @patch('utils.call_llm')
    def test_stateful_agents_maintain_state_in_shared_store(self, mock_llm):
        """Test that stateful agents continue to use shared store for state."""
        mock_llm.return_value = "Test result"
        
        analyst = AnalystNode()
        summarizer = SummarizerNode()
        
        # Start with empty shared store
        shared = {"input": "Test data"}
        
        # Run analyst first
        analyst.run(shared)
        
        # Verify analyst stored its result
        assert "analyst_result" in shared
        assert shared["analyst_result"] == "Test result"
        
        # Update input for summarizer
        shared["input"] = "Summary input"
        
        # Run summarizer
        summarizer.run(shared)
        
        # Verify both results are preserved in shared store
        assert "analyst_result" in shared
        assert "summarizer_result" in shared
        assert shared["analyst_result"] == "Test result"
        assert shared["summarizer_result"] == "Test result"
        
        # Last result should be from summarizer
        assert shared["last_result"] == "Test result"
    
    def test_dynamic_agent_loading_finds_existing_agents(self):
        """Test that dynamic loading can find existing stateful agents.""" 
        # Test loading analyst
        analyst_class = load_agent_class("analyst")
        analyst_instance = analyst_class()
        
        assert isinstance(analyst_instance, AnalystNode)
        assert hasattr(analyst_instance, 'run')
        assert hasattr(analyst_instance, 'prep')
        assert hasattr(analyst_instance, 'exec')
        assert hasattr(analyst_instance, 'post')
        
        # Test loading summarizer
        summarizer_class = load_agent_class("summarizer")
        summarizer_instance = summarizer_class()
        
        assert isinstance(summarizer_instance, SummarizerNode)
        assert hasattr(summarizer_instance, 'run')
    
    def test_existing_agents_not_compatible_with_stateless_endpoint(self):
        """Test that existing stateful agents aren't compatible with the stateless endpoint."""
        # This is expected behavior - old agents don't follow the new contract
        # They don't expect AgentRequest in the shared store
        
        analyst = AnalystNode()
        
        # Simulate what the stateless endpoint would put in shared store
        from generated.models import AgentRequest
        request = AgentRequest(
            context={"test": True},
            instructions="Test",
            execution_id="exec-compat",
            agent_id="analyst"
        )
        
        shared = {"agent_request": request}
        
        # Old agent should still work but will ignore the AgentRequest
        # It looks for "input" key in shared store
        with patch('utils.call_llm') as mock_llm:
            mock_llm.return_value = "Test result"
            result = analyst.run(shared)
        
        assert result == "default"
        # Should use empty string since no "input" key
        mock_llm.assert_called_once()
        call_args = mock_llm.call_args[0][0]
        assert "Input: " in call_args  # Empty input appended
    
    @patch('utils.call_llm')
    def test_mixed_stateful_and_stateless_workflow(self, mock_llm):
        """Test that stateful and stateless agents can coexist in same system."""
        mock_llm.return_value = "Mixed workflow test result"
        
        # Simulate a workflow where stateful agents run first
        shared = {"input": "Initial data"}
        
        analyst = AnalystNode()
        analyst.run(shared)
        
        # Verify stateful agent stored its result
        assert shared["analyst_result"] == "Mixed workflow test result"
        
        # Now simulate a stateless agent being called via the endpoint
        # (In practice this would be a separate HTTP call)
        from generated.models import AgentRequest, AgentResponse
        from generated.stateless_agent import StatelessAgent
        
        class MockStatelessAgent(StatelessAgent):
            def exec(self, prep_res):
                agent_request, memory_context, start_time = prep_res
                return {
                    "status": "completed",
                    "content": "Stateless agent processed the data",
                    "summary": "Stateless execution complete"
                }
        
        stateless_agent = MockStatelessAgent()
        
        # Prepare for stateless execution
        stateless_request = AgentRequest(
            context={"previous_analysis": shared.get("analyst_result", "")},
            instructions="Process previous analysis",
            execution_id="exec-mixed",
            agent_id="mock-stateless"
        )
        
        stateless_shared = {"agent_request": stateless_request}
        stateless_response = stateless_agent.run(stateless_shared)
        
        # Verify both types of agents worked
        assert isinstance(stateless_response, AgentResponse)
        assert stateless_response.status == "completed"
        assert "Stateless agent processed" in stateless_response.content
        
        # Original shared store unchanged by stateless execution
        assert shared["analyst_result"] == "Mixed workflow test result"
        
        # Stateless response stored in its shared store
        assert f"response_{stateless_request.execution_id}" in stateless_shared


class TestPerformanceRequirements:
    """Tests to verify sub-1 second execution requirement."""
    
    @patch('utils.call_llm')
    def test_stateful_agent_performance_baseline(self, mock_llm):
        """Establish performance baseline for existing stateful agents."""
        import time
        
        mock_llm.return_value = "Fast analysis result"
        
        agent = AnalystNode()
        shared = {"input": "Performance test data"}
        
        start_time = time.time()
        agent.run(shared)
        end_time = time.time()
        
        execution_time = end_time - start_time
        
        # Stateful agents should also be fast
        assert execution_time < 1.0  # Under 1 second
        
        # Usually much faster since we're mocking LLM
        assert execution_time < 0.1  # Under 100ms for mocked execution
    
    def test_stateless_agent_performance_requirement(self):
        """Test that stateless agents meet sub-1s performance requirement."""
        import time
        from generated.stateless_agent import StatelessAgent
        from generated.models import AgentRequest
        
        class FastStatelessAgent(StatelessAgent):
            def exec(self, prep_res):
                # Simulate some processing time but stay under 1s
                time.sleep(0.05)  # 50ms
                agent_request, memory_context, start_time = prep_res
                return {
                    "status": "completed", 
                    "content": "Fast execution completed",
                    "summary": "Performance test passed"
                }
        
        agent = FastStatelessAgent()
        request = AgentRequest(
            context={"performance": "test"},
            instructions="Fast execution test",
            execution_id="exec-perf",
            agent_id="fast-agent"
        )
        
        shared = {"agent_request": request}
        
        start_time = time.time()
        response = agent.run(shared)
        end_time = time.time()
        
        execution_time = end_time - start_time
        
        assert execution_time < 1.0  # Sub-1s requirement
        assert response.status == "completed"
        assert response.execution_time_ms is not None
        assert response.execution_time_ms < 1000
    
    def test_performance_monitoring_accuracy(self):
        """Test that performance monitoring accurately measures execution time."""
        import time
        from generated.stateless_agent import StatelessAgent
        from generated.models import AgentRequest
        
        class TimedStatelessAgent(StatelessAgent):
            def exec(self, prep_res):
                # Sleep for a known amount of time
                time.sleep(0.1)  # Exactly 100ms
                agent_request, memory_context, start_time = prep_res
                return {
                    "status": "completed",
                    "content": "Timed execution",
                    "summary": "Timing test"
                }
        
        agent = TimedStatelessAgent()
        request = AgentRequest(
            context={"timing": "test"},
            instructions="Timing test",
            execution_id="exec-timing",
            agent_id="timed-agent"
        )
        
        shared = {"agent_request": request}
        response = agent.run(shared)
        
        # Should be approximately 100ms (plus overhead)
        assert response.execution_time_ms >= 95  # At least 95ms 
        assert response.execution_time_ms <= 200  # No more than 200ms (accounting for overhead)
    
    def test_concurrent_execution_performance(self):
        """Test performance under concurrent execution load."""
        import time
        import concurrent.futures
        from generated.stateless_agent import StatelessAgent
        from generated.models import AgentRequest
        
        class ConcurrentTestAgent(StatelessAgent):
            def exec(self, prep_res):
                time.sleep(0.01)  # 10ms processing
                agent_request, memory_context, start_time = prep_res
                return {
                    "status": "completed",
                    "content": f"Processed {agent_request.execution_id}",
                    "summary": "Concurrent execution"
                }
        
        def run_agent(execution_id):
            agent = ConcurrentTestAgent()
            request = AgentRequest(
                context={"concurrent": True},
                instructions="Concurrent test",
                execution_id=execution_id,
                agent_id="concurrent-agent"
            )
            shared = {"agent_request": request}
            return agent.run(shared)
        
        # Run 10 agents concurrently
        start_time = time.time()
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [
                executor.submit(run_agent, f"exec-concurrent-{i}")
                for i in range(10)
            ]
            
            responses = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # All should complete successfully
        assert len(responses) == 10
        for response in responses:
            assert response.status == "completed"
            assert response.execution_time_ms < 1000  # Each under 1s
        
        # Total time should be less than 10 seconds (since they run concurrently)
        assert total_time < 5.0  # Should complete much faster than sequential
    
    def test_memory_usage_efficiency(self):
        """Test that stateless agents don't leak memory between executions."""
        import gc
        import psutil
        import os
        from generated.stateless_agent import StatelessAgent
        from generated.models import AgentRequest
        
        class MemoryTestAgent(StatelessAgent):
            def exec(self, prep_res):
                # Create some temporary data
                agent_request, memory_context, start_time = prep_res
                temp_data = "x" * 10000  # 10KB string
                return {
                    "status": "completed",
                    "content": f"Processed data of length {len(temp_data)}",
                    "summary": "Memory test execution"
                }
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        
        # Run many iterations
        for i in range(100):
            agent = MemoryTestAgent()
            request = AgentRequest(
                context={"iteration": i},
                instructions="Memory test",
                execution_id=f"exec-memory-{i}",
                agent_id="memory-agent"
            )
            shared = {"agent_request": request}
            response = agent.run(shared)
            
            assert response.status == "completed"
            
            # Explicitly clean up
            del agent, request, shared, response
        
        # Force garbage collection
        gc.collect()
        
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory
        
        # Memory increase should be minimal (less than 10MB)
        assert memory_increase < 10 * 1024 * 1024  # 10MB
        
        # Should not have increased significantly
        memory_increase_percent = (memory_increase / initial_memory) * 100
        assert memory_increase_percent < 50  # Less than 50% increase