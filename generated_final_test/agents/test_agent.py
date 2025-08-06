from pocketflow import Node
from utils import call_llm


class TestAgentNode(Node):
    """Simple test agent for integration testing"""

    def prep(self, shared):
        """Prepare input data for the agent."""
        return shared.get("input", "")

    def exec(self, prep_res):
        """Execute the agent with LLM call."""
        prompt = """You are a test agent. Your job is to:

1. Process the input
2. Return a simple response
3. Demonstrate basic functionality

This is used for testing the BMAD to PocketFlow conversion pipeline."""

        if prep_res:
            prompt = prompt + "\n\nInput: " + str(prep_res)

        return call_llm(prompt)

    def post(self, shared, prep_res, exec_res):
        """Store result and return action for flow control."""
        shared["test_agent_result"] = exec_res
        shared["last_result"] = exec_res
        return "default"
