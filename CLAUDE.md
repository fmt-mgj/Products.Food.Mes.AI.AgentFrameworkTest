# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 🔴 CRITICAL: PocketFlow Learning Resources - MUST USE

**⚠️ MANDATORY: When developing agents, you MUST actively consult these resources:**

1. **📖 Core Framework** (`pocketflow/__init__.py`)
   - The complete 100-line implementation defining ALL PocketFlow functionality
   - Contains: BaseNode, Node, BatchNode, Flow, BatchFlow, AsyncNode, AsyncFlow, Parallel variants
   - **ALWAYS reference this file to understand exact framework behavior**

2. **📚 Documentation** (`pocketflow_docs/`)
   - **Core Abstractions** (`pocketflow_docs/core_abstraction/`): Node lifecycle, Flow orchestration, Batch processing
   - **Design Patterns** (`pocketflow_docs/design_pattern/`): Agent, RAG, Multi-agent, MapReduce patterns
   - **Utility Functions** (`pocketflow_docs/utility_function/`): LLM calls, embeddings, chunking, etc.
   - **MUST read relevant docs before implementing any pattern**

3. **🍳 Cookbook Examples** (`cookbook/`)
   - **40+ working examples** demonstrating every PocketFlow pattern
   - Each example includes: `flow.py`, `nodes.py`, `utils/`, `requirements.txt`
   - **CRITICAL: Study similar examples before implementing new features**
   - Key examples to review:
     - `pocketflow-agent/`: Basic agent with decision-making
     - `pocketflow-multi-agent/`: Supervisor pattern
     - `pocketflow-fastapi-*`: REST API integration patterns
     - `pocketflow-async-*`: Async/parallel processing
     - `pocketflow-batch-*`: Batch processing patterns

**Development Workflow:**
1. First, read the 100-line `pocketflow/__init__.py` to understand core mechanics
2. Then, consult `pocketflow_docs/` for the specific pattern you're implementing
3. Finally, examine relevant `cookbook/` examples for practical implementation patterns
4. Use these patterns directly in your implementation - don't reinvent the wheel!

## CRITICAL: Project Boundaries

**DO NOT MODIFY:**
- ❌ **PocketFlow Core** (`pocketflow/__init__.py`) - This is a fixed 100-line framework
- ❌ **BMAD Methodology** (`.bmad-core/`) - This is the established method, not to be changed
- ❌ **Core Config** (`.bmad-core/core-config.yaml`) - Framework configuration

**ONLY DEVELOP:**
- ✅ **Generator** (`scripts/bmad2pf.py` and related) - The converter from preprocessing to PocketFlow
- ✅ **Runtime** (`generated/app.py` and templates) - The FastAPI runtime for agents
- ✅ **Project Preprocessing Files** (`preprocessing/`) - User's specific agent definitions
- ✅ **Documentation** (`docs/`) - PRD, Architecture, and related docs

## Repository Overview

This project implements the **BMAD → PocketFlow Generator & Runtime**, which converts BMAD methodology artifacts (Markdown prompts, checklists, workflows) into executable PocketFlow code. It provides:

1. **CLI Generator** that parses BMAD files and generates PocketFlow code in <1 second
2. **FastAPI Runtime** that executes generated agents with REST API endpoints
3. **Document Management** for dynamic Markdown input/output
4. **Memory System** with isolation and persistence

The project uses PocketFlow as the underlying execution framework but does NOT modify it. PocketFlow is a minimalist 100-line LLM framework that implements core abstractions (Node, Flow, Batch, Async) to build complex AI applications using simple graph-based patterns.

## Project-Specific Development Commands

### Generator Commands
```bash
# Generate PocketFlow code from BMAD files
python scripts/bmad2pf.py --src ./preprocessing --out ./generated

# Validate BMAD files without generating
python scripts/bmad2pf.py --src ./preprocessing --check

# Generate with verbose output
python scripts/bmad2pf.py --src ./preprocessing --out ./generated --verbose
```

### Runtime Commands
```bash
# Start the FastAPI development server
uvicorn generated.app:app --reload --port 8000

# Run production server
uvicorn generated.app:app --host 0.0.0.0 --port 8000 --workers 4
```

### Testing Commands
```bash
# Run generator tests
python -m pytest tests/unit/test_generator.py

# Run runtime tests
python -m pytest tests/integration/test_api.py

# Run all tests with coverage
python -m pytest tests/ --cov=scripts --cov=generated

# Run performance tests
python -m pytest tests/performance/ -v
```

### Docker Commands
```bash
# Build container
docker build -t bmad-pocketflow .

# Run container locally
docker run -p 8000:8000 --env-file .env bmad-pocketflow

# Deploy to Railway
railway up --service bmad-backend
```

### Dependencies
The core framework has zero dependencies. Individual cookbook examples may require:
- `openai`, `anthropic`, `google-genai` for LLM providers
- `pyyaml` for structured output parsing
- `pytest` for testing
- Additional dependencies per cookbook example (see individual requirements.txt files)

## Architecture & Code Structure

### Core Framework (`pocketflow/__init__.py`)
The entire framework is 100 lines implementing:

1. **BaseNode**: Foundation for all nodes with prep/exec/post lifecycle
2. **Node**: Regular node with retry/fallback support
3. **BatchNode**: Processes iterables item by item
4. **Flow**: Orchestrates node graphs with action-based transitions
5. **BatchFlow**: Runs flows multiple times with different parameters
6. **AsyncNode/AsyncFlow**: Async versions for I/O-bound operations
7. **AsyncParallelBatch***: Parallel processing variants

### Key Design Patterns

#### Node Lifecycle (prep → exec → post)
- `prep(shared)`: Read from shared store, prepare data
- `exec(prep_res)`: Execute logic (LLM calls, computations) - should be idempotent if retries enabled
- `post(shared, prep_res, exec_res)`: Write results, return action string for flow control

#### Flow Transitions
- Default: `node_a >> node_b`
- Named actions: `node_a - "action_name" >> node_b`
- Branching: Multiple actions from one node to different targets

#### Communication
- **Shared Store**: Global dict for data exchange between nodes (primary method)
- **Params**: Per-node configuration for batch processing identifiers

### Project Structure for New Applications

When building new LLM applications:

```
my_project/
├── main.py           # Entry point
├── nodes.py          # Node implementations
├── flow.py           # Flow assembly
├── utils/            # Utility functions
│   ├── __init__.py
│   ├── call_llm.py   # LLM wrapper
│   └── [other_utils].py
├── docs/
│   └── design.md     # High-level design doc
└── requirements.txt
```

### Development Guidelines from .cursorrules

1. **Start Simple**: Begin with minimal implementation, iterate
2. **Design First**: Create `docs/design.md` before implementation
3. **Separation of Concerns**: Keep data (shared store) separate from logic (nodes)
4. **Fail Fast**: Let Node retry mechanism handle errors, avoid try/except in utilities
5. **Human Design, Agent Code**: Humans specify high-level flow, AI implements details

### Common Utility Patterns

#### LLM Call Pattern
```python
def call_llm(prompt):
    # Implementation varies by provider
    # Should handle rate limits via Node retry mechanism
    # Avoid caching if using retries
```

#### Structured Output Pattern
```python
# Use YAML for better escaping handling
prompt = f"""
Output in yaml:
```yaml
key: value
```"""
response = call_llm(prompt)
yaml_str = response.split("```yaml")[1].split("```")[0]
result = yaml.safe_load(yaml_str)
# Add assertions for validation
```

### Testing Approach

Tests in `tests/` directory cover:
- Basic flow operations (sequencing, branching)
- Batch processing (node and flow level)
- Async operations
- Parallel processing
- Error handling and fallbacks
- Flow composition

### Cookbook Examples

The `cookbook/` directory contains 40+ examples demonstrating:
- Basic patterns: chat, RAG, agents, workflows
- Advanced patterns: multi-agent, supervisor, parallel processing
- Integration examples: FastAPI, Streamlit, voice chat
- Tool usage: search, database, embeddings, vision

Each cookbook example follows the same structure with its own flow.py, nodes.py, utils/, and requirements.txt.

## BMAD → PocketFlow Generator Architecture

### 🎯 CRITICAL: Using PocketFlow Resources for BMAD Conversion

When converting BMAD agents to PocketFlow nodes, **ALWAYS**:

1. **Map BMAD Agent Types to PocketFlow Patterns:**
   - Simple prompt-based agents → Study `cookbook/pocketflow-agent/`
   - Agents with dependencies → Study `cookbook/pocketflow-supervisor/`
   - Parallel agents → Study `cookbook/pocketflow-async-parallel-batch/`
   - Workflow agents → Study `cookbook/pocketflow-workflow/`

2. **Reference Documentation for Each Feature:**
   - Memory persistence → `pocketflow_docs/core_abstraction/communication.md`
   - Flow transitions → `pocketflow_docs/core_abstraction/flow.md`
   - Async execution → `pocketflow_docs/core_abstraction/async.md`
   - Batch processing → `pocketflow_docs/core_abstraction/batch.md`

3. **Copy Patterns from Cookbook:**
   - Don't create new patterns - use existing ones from cookbook
   - Each cookbook example is production-tested
   - Modify cookbook patterns to fit BMAD requirements

### Key Subsystems to Implement

1. **BMAD Parser** (`scripts/parser.py`)
   - Parse Markdown files with YAML front-matter
   - Extract agent metadata (id, tools, memory_scope, dependencies)
   - Preserve prompt content after front-matter

2. **Code Generator** (`scripts/generator.py`)
   - Use Jinja2 templates to generate Python code
   - Create PocketFlow Node classes from BMAD agents
   - Generate FastAPI application with all endpoints

3. **FastAPI Runtime** (`generated/app.py`)
   - `/run` endpoint for flow execution
   - `/doc/*` endpoints for document management
   - `/memory/*` endpoints for debugging
   - Stream support for long-running flows

4. **Memory Manager** (`generated/memory.py`)
   - File-based storage with JSONL format
   - Isolation scopes (per agent/story or shared)
   - Cache in RAM during flow execution

5. **Flow Executor** (`generated/executor.py`)
   - Dependency checking before agent execution
   - Parallel execution with asyncio.TaskGroup
   - Error handling and retry logic

### Implementation Order (Following Epics)

1. **Epic 1: Foundation & CLI Generator**
   - Set up project structure
   - Implement BMAD parser
   - Create Jinja templates
   - Build CLI tool

2. **Epic 2: FastAPI Runtime & Core API**
   - Bootstrap FastAPI application
   - Implement document storage API
   - Create memory storage system
   - Add flow execution endpoint

3. **Epic 3: Agent Orchestration**
   - Add dependency resolution
   - Implement parallel execution
   - Create comprehensive flow orchestration
   - Add streaming responses

4. **Epic 4: Deployment & Operations**
   - Create Dockerfile
   - Set up GitHub Actions
   - Configure cloud deployments
   - Add monitoring

### Critical Implementation Rules

1. **Never modify PocketFlow core** - Only use it as imported
2. **Generated code is disposable** - Can regenerate anytime from BMAD sources
3. **Configuration is preserved** - Never overwrite `runtime.yaml`
4. **BMAD files are source of truth** - All logic derives from these
5. **Keep it simple** - Minimal dependencies, straightforward code

### File References

- **PRD**: `docs/prd.md` - Product requirements
- **Architecture**: `docs/architecture.md` - System design
- **Tech Stack**: `docs/architecture/tech-stack.md` - Technology choices
- **Coding Standards**: `docs/architecture/coding-standards.md` - Code style
- **Source Tree**: `docs/architecture/source-tree.md` - Project structure

## Important Notes

- The framework is intentionally minimal - no vendor lock-in or built-in integrations
- All LLM/tool integrations should be implemented as utility functions
- Use Node retry mechanism instead of try/except in utilities
- Prefer YAML over JSON for structured outputs (better string handling)
- Always validate structured outputs with assertions in exec()
- For parallel operations, be mindful of rate limits on external APIs
- **Generation must complete in under 1 second** - This is a hard requirement
- **Use async/await throughout** - For all I/O operations
- **Test coverage minimum 80%** - Especially for core modules

## 📌 Quick Reference Paths

**Essential Files to Keep Open While Developing:**
- Core Framework: `pocketflow/__init__.py` (100 lines)
- Type Hints: `pocketflow/__init__.pyi`
- Documentation Index: `pocketflow_docs/index.md`
- Cookbook Index: `cookbook/README.md`
- Similar Example: `cookbook/pocketflow-[pattern-name]/`

**When stuck, check these in order:**
1. The 100-line core (`pocketflow/__init__.py`)
2. Relevant documentation (`pocketflow_docs/`)
3. Working cookbook example (`cookbook/`)
4. Test files for usage patterns (`tests/`)