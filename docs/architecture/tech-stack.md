# BMAD → PocketFlow Generator & Runtime - Technology Stack

## Overview

This document defines the complete technology stack for the BMAD → PocketFlow Generator & Runtime system. The stack is intentionally minimal, following the KISS (Keep It Simple, Stupid) principle while providing all necessary capabilities for production deployment.

## Core Technologies

### Programming Language

**Python 3.10+**
- **Rationale**: Modern async/await support, type hints, structural pattern matching
- **Version Policy**: Minimum 3.10, tested up to 3.12
- **Key Features Used**:
  - Native async/await for concurrent operations
  - Type hints for better IDE support and documentation
  - Data classes for clean data models
  - Union types and Optional for explicit null handling

### Frameworks

#### Application Framework

**FastAPI 0.104+**
- **Purpose**: REST API server with automatic documentation
- **Key Features**:
  - Automatic OpenAPI/Swagger documentation
  - Pydantic integration for request/response validation
  - Native async support
  - Dependency injection system
  - WebSocket support for future streaming needs
- **Configuration**:
  ```python
  app = FastAPI(
      title="BMAD PocketFlow Runtime",
      version="0.31",
      docs_url="/docs",
      redoc_url="/redoc"
  )
  ```

#### LLM Framework

**PocketFlow (Custom, 100 lines)**
- **Purpose**: Minimal LLM orchestration framework
- **Components**:
  - BaseNode: Foundation for all nodes
  - Node: Regular node with retry/fallback
  - BatchNode: Batch processing capability
  - Flow: Graph-based orchestration
  - AsyncNode/AsyncFlow: Async variants
- **No External Dependencies**: Pure Python implementation

#### ASGI Server

**Uvicorn 0.24+**
- **Purpose**: Production ASGI server for FastAPI
- **Configuration**:
  ```python
  uvicorn.run(
      app,
      host="0.0.0.0",
      port=8000,
      workers=4,
      loop="auto",
      log_config=log_config
  )
  ```

## Code Generation Stack

### Template Engine

**Jinja2 3.1+**
- **Purpose**: Generate Python code from templates
- **Templates**:
  - `agent.py.j2`: Agent class generation
  - `app.py.j2`: FastAPI application
  - `tools.py.j2`: Tool registration
- **Features Used**:
  - Template inheritance
  - Macros for code reuse
  - Filters for string manipulation
  - Safe string handling

### Parsing Libraries

**PyYAML 6.0+**
- **Purpose**: Parse YAML front matter and configuration files
- **Security**: Always use `yaml.safe_load()` to prevent code injection
- **Files Parsed**:
  - Markdown front matter
  - `workflow.yaml`
  - `tools.yaml`
  - `runtime.yaml`

**Python-Markdown 3.5+** (Optional)
- **Purpose**: Parse Markdown structure if needed
- **Usage**: Extract content sections, parse headers

### Code Quality Tools

**Black 23.12+**
- **Purpose**: Opinionated code formatter
- **Configuration**:
  ```toml
  [tool.black]
  line-length = 88
  target-version = ['py310']
  ```

**Ruff 0.1.8+**
- **Purpose**: Fast Python linter
- **Configuration**:
  ```toml
  [tool.ruff]
  line-length = 88
  select = ["E", "F", "I", "N", "W"]
  ```

## Data Management

### Request/Response Validation

**Pydantic 2.5+**
- **Purpose**: Data validation and settings management
- **Models**:
  ```python
  class FlowRequest(BaseModel):
      flow: str = "default"
      input: str
      story_id: str
  ```
- **Features**: Automatic validation, JSON schema generation, type coercion

### File Operations

**aiofiles 23.2+**
- **Purpose**: Async file I/O operations
- **Usage**: Document reading/writing, memory persistence
- **Pattern**:
  ```python
  async with aiofiles.open(path, mode='r') as f:
      content = await f.read()
  ```

### Data Formats

**JSON Lines (JSONL)**
- **Purpose**: Append-only memory storage
- **Rationale**: Human-readable, streamable, corruption-resistant
- **Structure**: One JSON object per line

**Markdown**
- **Purpose**: All documentation and agent prompts
- **Rationale**: Human-readable, version-control friendly, universal

## Storage Backends

### Default: File System

**Local File Storage**
- **Documents**: `/docs/*.md`
- **Memory**: `/memory/*.jsonl`
- **Configuration**: `/config/*.yaml`
- **Rationale**: Zero dependencies, easy debugging, git-compatible

### Optional: Redis

**Redis 7.0+** (Optional)
- **Purpose**: Distributed memory backend for scaling
- **Library**: `redis-py` with async support
- **Configuration**:
  ```python
  redis = aioredis.from_url(
      "redis://localhost:6379",
      decode_responses=True
  )
  ```

## Development Tools

### Testing

**Pytest 7.4+**
- **Purpose**: Testing framework
- **Plugins**:
  - `pytest-asyncio`: Async test support
  - `pytest-cov`: Coverage reporting
  - `pytest-mock`: Mocking utilities
- **Configuration**:
  ```ini
  [tool.pytest.ini_options]
  asyncio_mode = "auto"
  testpaths = ["tests"]
  ```

**Coverage.py 7.3+**
- **Purpose**: Code coverage measurement
- **Target**: Minimum 80% coverage for core modules

### Development Dependencies

**Pre-commit 3.5+**
- **Purpose**: Git hooks for code quality
- **Hooks**: Black, Ruff, YAML validation

**Python-dotenv 1.0+**
- **Purpose**: Load environment variables from `.env` files
- **Usage**: Development environment configuration

## Deployment Stack

### Containerization

**Docker 24.0+**
- **Purpose**: Container packaging and deployment
- **Features**:
  - Multi-stage builds for size optimization
  - Layer caching for faster builds
  - Health checks for orchestration
- **Base Image**: `python:3.10-slim`

### CI/CD

**GitHub Actions**
- **Purpose**: Automated testing and deployment
- **Workflows**:
  - On push: Test, build, deploy
  - On PR: Test, lint, coverage
  - Scheduled: Dependency updates

### Container Registries

**GitHub Container Registry (ghcr.io)**
- **Purpose**: Docker image storage
- **Integration**: Automatic with GitHub Actions

### Deployment Platforms

**Railway**
- **Configuration**: `railway.toml`
- **Features**: Automatic deploys, environment management

**Fly.io**
- **Configuration**: `fly.toml`
- **Features**: Global distribution, automatic scaling

**Google Cloud Run**
- **Configuration**: Service YAML
- **Features**: Serverless, pay-per-use

## LLM Provider Integrations

### Primary Providers

**OpenAI API**
- **Library**: `openai` 1.6+
- **Models**: GPT-4, GPT-3.5-turbo
- **Features**: Streaming, function calling

**Anthropic API**
- **Library**: `anthropic` 0.8+
- **Models**: Claude 3 family
- **Features**: Large context windows

**Google AI**
- **Library**: `google-generativeai` 0.3+
- **Models**: Gemini family
- **Features**: Multimodal support

### Provider Abstraction

**LiteLLM** (Optional)
- **Purpose**: Unified interface for multiple LLM providers
- **Benefits**: Provider switching, fallback support, cost tracking

## Monitoring & Observability

### Logging

**Python Logging Module**
- **Purpose**: Structured logging throughout application
- **Format**: JSON for production, readable for development
- **Levels**: DEBUG, INFO, WARNING, ERROR, CRITICAL

**Loguru** (Alternative)
- **Purpose**: Simpler logging with better defaults
- **Features**: Automatic rotation, structured logging

### Metrics (Future)

**OpenTelemetry** (Prepared, not required)
- **Purpose**: Distributed tracing and metrics
- **Integration Points**: API endpoints, LLM calls, memory operations

**Prometheus** (Future)
- **Purpose**: Time-series metrics
- **Metrics**: Request latency, agent execution time, memory usage

## Security Tools

### Secret Management

**Environment Variables**
- **Purpose**: API keys and sensitive configuration
- **Files**: `.env` (development), platform-specific (production)

### Input Validation

**Pydantic** (Already listed)
- **Purpose**: Automatic input validation and sanitization

### Security Scanning

**Bandit** (Development)
- **Purpose**: Security linting for Python code
- **Integration**: Pre-commit hook

**Safety** (Development)
- **Purpose**: Check dependencies for known vulnerabilities
- **Integration**: CI/CD pipeline

## Version Management

### Package Management

**pip + requirements.txt**
- **Purpose**: Dependency management
- **Files**:
  - `requirements.txt`: Production dependencies
  - `requirements-dev.txt`: Development dependencies

**Poetry** (Alternative)
- **Purpose**: Modern dependency management
- **Benefits**: Lock files, virtual env management

### Version Pinning Policy

```txt
# requirements.txt
fastapi==0.104.1        # Exact version for framework
pydantic>=2.5.0,<3.0.0  # Minor version flexibility
pyyaml>=6.0             # Minimum version only
```

## Platform Requirements

### Operating System

- **Development**: Windows 10+, macOS 11+, Ubuntu 20.04+
- **Production**: Linux (Alpine preferred for containers)

### Runtime Requirements

- **Python**: 3.10+ (3.11 recommended)
- **Memory**: 512MB minimum, 1GB recommended
- **CPU**: 1 core minimum, 2+ for parallel execution
- **Disk**: 100MB for application, 1GB+ for documents/memory

## Technology Decision Matrix

| Category | Chosen | Alternatives Considered | Rationale |
|----------|--------|------------------------|-----------|
| Language | Python 3.10+ | Node.js, Go | Ecosystem, async support, simplicity |
| Framework | FastAPI | Flask, Django | Modern, async, auto-docs |
| Template | Jinja2 | Mako, string.Template | Mature, flexible, familiar |
| Server | Uvicorn | Gunicorn, Hypercorn | FastAPI native, performance |
| Format | YAML | TOML, JSON | Human-readable, complex structures |
| Storage | File + Redis | PostgreSQL, MongoDB | Simplicity, optional scaling |
| Container | Docker | Podman | Industry standard, ecosystem |
| CI/CD | GitHub Actions | GitLab CI, Jenkins | GitHub integration, free tier |

## Upgrade Path

### Near-term (3-6 months)
- Redis for distributed memory
- OpenTelemetry for observability
- LiteLLM for provider abstraction

### Medium-term (6-12 months)
- PostgreSQL for persistent storage
- Kubernetes for orchestration
- GraphQL API alongside REST

### Long-term (12+ months)
- Event-driven architecture
- Micro-frontends
- Multi-region deployment

## Dependency Security

### Update Policy
- **Security patches**: Immediate
- **Minor versions**: Monthly review
- **Major versions**: Quarterly evaluation

### Vulnerability Scanning
- **Dependabot**: Automated PR for updates
- **Safety check**: CI/CD pipeline validation
- **OWASP scanning**: Quarterly audit

---

*This technology stack document is maintained by the architecture team and updated with each major version release.*