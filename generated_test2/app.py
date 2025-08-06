from agents.test_agent import TestAgentNode
from fastapi import FastAPI
from pydantic import BaseModel

from pocketflow import Flow

app = FastAPI(title="BMAD PocketFlow Runtime", version="1.0.0")


class RunRequest(BaseModel):
    input: str = ""


class RunResponse(BaseModel):
    result: str
    agent_results: dict


@app.get("/health")
def health():
    """Health check endpoint."""
    return {"status": "ok", "service": "bmad-pocketflow-runtime"}


@app.post("/run", response_model=RunResponse)
def run_flow(request: RunRequest):
    """Execute the agent flow with the provided input."""

    # Initialize shared store
    shared = {"input": request.input}

    # Create flow with sequential execution
    flow = Flow()

    # Create and chain agent nodes
    test_agent_node = TestAgentNode()

    # Chain nodes sequentially
    flow.start(test_agent_node)

    # Execute the flow
    result = flow.run(shared)

    # Collect all agent results
    agent_results = {}
    if "test_agent_result" in shared:
        agent_results["test_agent"] = shared["test_agent_result"]

    return RunResponse(
        result=shared.get("last_result", str(result)), agent_results=agent_results
    )
