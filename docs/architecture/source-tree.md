# BMAD → PocketFlow Generator & Runtime - Source Tree

## Project Structure Overview

This document defines the complete source tree structure for the BMAD → PocketFlow Generator & Runtime system. The structure emphasizes clear separation between user-editable BMAD sources, generated code, and runtime data.

## Complete Source Tree

```
bmad-pocketflow/
├── .github/                       # GitHub specific files
│   ├── workflows/                 # CI/CD workflows
│   │   ├── deploy.yml            # Main deployment pipeline
│   │   ├── test.yml              # Testing workflow
│   │   └── release.yml           # Release automation
│   ├── ISSUE_TEMPLATE/           # Issue templates
│   └── PULL_REQUEST_TEMPLATE.md  # PR template
│
├── .bmad-core/                    # BMAD framework core files
│   ├── core-config.yaml          # Core configuration
│   ├── agents/                   # Reusable agent templates
│   ├── tasks/                    # Common tasks
│   ├── templates/                # Document templates
│   └── checklists/               # Standard checklists
│
├── bmad/                          # BMAD source files (user-edited)
│   ├── agents/                   # Agent definitions
│   │   ├── analyst.md           # Analyst agent with YAML front matter
│   │   ├── architect.md         # Architect agent
│   │   ├── reviewer.md          # Code reviewer agent
│   │   └── tester.md            # Testing agent
│   ├── checklists/               # Project-specific checklists
│   │   ├── deployment.md        # Deployment checklist
│   │   └── review.md            # Review checklist
│   ├── workflows/                # Workflow definitions
│   │   └── default.yaml         # Default workflow configuration
│   └── tools.yaml                # Custom tool definitions
│
├── config/                        # Runtime configuration (preserved)
│   ├── runtime.yaml              # Runtime settings (never overwritten)
│   ├── secrets.env               # API keys and secrets
│   └── logging.yaml              # Logging configuration
│
├── docs/                          # Documentation and runtime documents
│   ├── architecture/             # Architecture documentation
│   │   ├── coding-standards.md  # Coding standards
│   │   ├── tech-stack.md        # Technology stack
│   │   └── source-tree.md       # This file
│   ├── architecture.md           # Main architecture document
│   ├── prd.md                   # Product requirements document
│   ├── README.md                # Project documentation
│   └── *.md                     # Runtime-generated documents
│
├── generated/                     # Generated code (never edit manually)
│   ├── __init__.py              # Package initialization
│   ├── app.py                   # FastAPI application
│   ├── agents/                  # Generated agent modules
│   │   ├── __init__.py
│   │   ├── analyst.py           # Generated from analyst.md
│   │   ├── architect.py         # Generated from architect.md
│   │   ├── reviewer.py          # Generated from reviewer.md
│   │   └── tester.py            # Generated from tester.md
│   ├── executor.py              # Flow execution engine
│   ├── memory.py                # Memory management
│   ├── documents.py             # Document store
│   ├── models.py                # Pydantic models
│   ├── tools.py                 # Generated tool registrations
│   └── utils.py                 # Utility functions
│
├── memory/                        # Runtime memory storage
│   ├── isolated/                # Isolated agent memory
│   │   └── {agent}_{story}.jsonl
│   └── shared/                  # Shared namespace memory
│       └── {namespace}.jsonl
│
├── scripts/                       # Generator and utility scripts
│   ├── bmad2pf.py               # Main generator CLI
│   ├── parser.py                # BMAD file parser
│   ├── config_loader.py         # Configuration loader
│   ├── generator.py             # Code generation logic
│   ├── formatter.py             # Code formatting utilities
│   ├── templates/               # Jinja2 templates
│   │   ├── agent.py.j2          # Agent class template
│   │   ├── app.py.j2            # FastAPI app template
│   │   ├── executor.py.j2       # Executor template
│   │   ├── memory.py.j2         # Memory manager template
│   │   └── tools.py.j2          # Tools registration template
│   └── utils/                   # Script utilities
│       ├── __init__.py
│       └── validation.py        # Validation helpers
│
├── tests/                         # Test suite
│   ├── __init__.py
│   ├── conftest.py              # Pytest configuration
│   ├── unit/                    # Unit tests
│   │   ├── test_parser.py       # Parser tests
│   │   ├── test_generator.py    # Generator tests
│   │   ├── test_memory.py       # Memory tests
│   │   └── test_executor.py     # Executor tests
│   ├── integration/             # Integration tests
│   │   ├── test_flow.py         # Flow execution tests
│   │   ├── test_api.py          # API endpoint tests
│   │   └── test_parallel.py     # Parallel execution tests
│   ├── performance/             # Performance tests
│   │   └── test_generation.py   # Generation speed tests
│   └── fixtures/                # Test fixtures
│       ├── sample_agents/       # Sample BMAD files
│       ├── mock_responses/      # Mock LLM responses
│       └── test_docs/           # Test documents
│
├── deployment/                    # Deployment configurations
│   ├── docker/                  # Docker-related files
│   │   ├── Dockerfile           # Main container definition
│   │   └── .dockerignore        # Docker ignore file
│   ├── railway.toml             # Railway configuration
│   ├── fly.toml                 # Fly.io configuration
│   └── k8s/                     # Kubernetes manifests (future)
│       ├── deployment.yaml
│       └── service.yaml
│
├── .ai/                          # AI-related metadata
│   ├── debug-log.md             # Debug log for AI agents
│   └── context/                 # Context for AI assistance
│
├── .vscode/                      # VS Code configuration
│   ├── settings.json            # Workspace settings
│   ├── launch.json              # Debug configurations
│   └── extensions.json          # Recommended extensions
│
├── cookbook/                     # Example implementations
│   ├── basic/                   # Basic examples
│   │   ├── hello_world/         # Minimal example
│   │   └── simple_flow/         # Simple flow example
│   └── advanced/                # Advanced patterns
│       ├── parallel_agents/     # Parallel execution
│       └── multi_llm/           # Multiple LLM providers
│
├── utils/                        # Shared utilities
│   ├── __init__.py
│   ├── llm_clients.py          # LLM provider wrappers
│   ├── validators.py           # Input validators
│   └── helpers.py              # Helper functions
│
├── .env.example                  # Example environment variables
├── .gitignore                   # Git ignore file
├── .pre-commit-config.yaml      # Pre-commit hooks
├── LICENSE                      # License file
├── Makefile                     # Common tasks automation
├── pyproject.toml               # Python project configuration
├── README.md                    # Project README
├── requirements.txt             # Production dependencies
├── requirements-dev.txt         # Development dependencies
├── setup.py                     # Package setup file
└── VERSION                      # Version file
```

## Directory Descriptions

### Core Directories

#### `/bmad/`
**Purpose**: User-editable BMAD source files  
**Contents**: Markdown agents, checklists, workflows  
**Access**: Read-only by generator, editable by users  
**Version Control**: Always committed to git

#### `/generated/`
**Purpose**: Output from the generator  
**Contents**: Python modules for runtime  
**Access**: Written by generator, read by runtime  
**Version Control**: Listed in .gitignore, never committed

#### `/config/`
**Purpose**: Runtime configuration  
**Contents**: YAML configs, environment files  
**Access**: Read by runtime, manually edited  
**Version Control**: Templates committed, secrets in .gitignore

#### `/scripts/`
**Purpose**: Generator implementation  
**Contents**: Parser, generator, templates  
**Access**: Executable scripts  
**Version Control**: Always committed

#### `/docs/`
**Purpose**: Documentation and runtime documents  
**Contents**: Architecture, PRD, runtime-generated docs  
**Access**: Read/write by runtime for dynamic docs  
**Version Control**: Static docs committed, runtime docs optional

### Runtime Directories

#### `/memory/`
**Purpose**: Agent memory storage  
**Contents**: JSONL files with agent state  
**Access**: Read/write by runtime  
**Version Control**: Never committed (in .gitignore)

#### `/deployment/`
**Purpose**: Deployment configurations  
**Contents**: Docker, platform configs  
**Access**: Read-only  
**Version Control**: Always committed

### Development Directories

#### `/tests/`
**Purpose**: Test suite  
**Contents**: Unit, integration, performance tests  
**Access**: Executable by pytest  
**Version Control**: Always committed

#### `/cookbook/`
**Purpose**: Example implementations  
**Contents**: Sample BMAD projects  
**Access**: Reference only  
**Version Control**: Always committed

#### `/.bmad-core/`
**Purpose**: BMAD framework core files  
**Contents**: Reusable templates and configurations  
**Access**: Read-only reference  
**Version Control**: Always committed

## File Naming Conventions

### BMAD Files
- Agents: `{agent_name}.md` (lowercase, underscore-separated)
- Checklists: `{checklist_name}.md`
- Workflows: `{workflow_name}.yaml`

### Generated Files
- Python modules: `{source_name}.py`
- Same structure as source with `.py` extension

### Documentation
- Markdown files: `{document_name}.md` (kebab-case for multi-word)
- Architecture docs: Under `/docs/architecture/`

### Test Files
- Test modules: `test_{module_name}.py`
- Fixtures: Descriptive names in `/tests/fixtures/`

## Special Files

### `.gitignore`
```gitignore
# Generated code
/generated/

# Runtime data
/memory/
/docs/*.md
!/docs/architecture/
!/docs/prd.md
!/docs/README.md

# Secrets
.env
secrets.env
*.key
*.pem

# Python
__pycache__/
*.pyc
.pytest_cache/
.coverage
*.egg-info/

# IDE
.vscode/
.idea/
*.swp

# OS
.DS_Store
Thumbs.db
```

### `Makefile`
```makefile
.PHONY: generate run test clean

generate:
	python scripts/bmad2pf.py --src ./bmad --out ./generated

run: generate
	uvicorn generated.app:app --reload

test:
	pytest tests/ -v --cov=generated

clean:
	rm -rf generated/ __pycache__ .pytest_cache
	find . -type f -name "*.pyc" -delete

format:
	black scripts/ tests/
	ruff --fix scripts/ tests/

docker-build:
	docker build -t bmad-pocketflow .

docker-run: docker-build
	docker run -p 8000:8000 --env-file .env bmad-pocketflow
```

## Directory Permissions

### Development Environment
```bash
# Read/write for user
chmod -R u+rw .

# Generated directory is replaceable
chmod -R u+rw generated/

# Config files need protection
chmod 600 config/secrets.env
```

### Production Container
```dockerfile
# Non-root user
RUN useradd -m -u 1000 appuser

# Appropriate permissions
RUN chown -R appuser:appuser /app
RUN chmod -R 755 /app
RUN chmod 600 /app/config/secrets.env

USER appuser
```

## File Size Guidelines

### Source Files
- BMAD agents: < 10KB each
- Workflows: < 5KB
- Configuration: < 2KB

### Generated Files
- Python modules: < 50KB each
- Total generated: < 500KB

### Runtime Files
- Documents: < 100KB each
- Memory entries: < 1MB per story
- Logs: Rotate at 10MB

## Backup Strategy

### Critical (Always Backup)
- `/bmad/` - Source files
- `/config/runtime.yaml` - Configuration
- `/docs/architecture/` - Documentation

### Important (Regular Backup)
- `/docs/` - Runtime documents
- `/memory/shared/` - Shared memory

### Regeneratable (No Backup Needed)
- `/generated/` - Can regenerate from source
- `/memory/isolated/` - Transient data
- `__pycache__/` - Python cache

## CI/CD Artifacts

### Build Artifacts
```
artifacts/
├── bmad-pocketflow-{version}.tar.gz  # Source archive
├── generated-{commit}.zip            # Generated code
└── docker-image-{commit}.tar         # Docker image
```

### Test Reports
```
reports/
├── coverage.xml                      # Coverage report
├── pytest-report.xml                 # Test results
└── performance-{date}.json           # Performance metrics
```

## Development Workflow Paths

### Feature Development
1. Edit files in `/bmad/`
2. Run generator: `scripts/bmad2pf.py`
3. Test locally: `/generated/app.py`
4. Write tests: `/tests/`
5. Commit changes (excluding `/generated/`)

### Debugging Flow
1. Check logs: `.ai/debug-log.md`
2. Inspect generated: `/generated/`
3. Review memory: `/memory/`
4. Test isolated: `/tests/fixtures/`

### Deployment Path
1. Source: `/bmad/` → 
2. Generate: `/generated/` →
3. Package: `/deployment/docker/` →
4. Deploy: Platform-specific config

---

*This source tree structure is designed for clarity, maintainability, and clear separation of concerns. Follow these conventions for consistent project organization.*