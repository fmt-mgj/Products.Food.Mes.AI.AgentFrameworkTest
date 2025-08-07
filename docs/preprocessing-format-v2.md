# BMAD Preprocessing Format v2.0 Specification

## Overview

The enhanced preprocessing format v2.0 preserves familiar BMAD terminology while enabling sophisticated agent workflows with deterministic PocketFlow execution. This format maintains full backward compatibility with v1.0 while adding powerful new capabilities.

## Format Structure

### Basic YAML Front-matter Structure

```yaml
---
# Core identification (required)
id: agent_name                    # Unique agent identifier
description: "Agent purpose"      # Brief role description

# BMAD terminology fields (optional)
persona: "Role and expertise context"
tasks: ["task1.md", "task2.md"]           # Task definition files  
checklists: ["quality.md", "review.md"]   # Validation checklists
templates: ["output.md", "report.md"]     # Output templates
commands: ["*analyze", "*validate"]       # Available commands

# Execution configuration
tools: ["text_splitter", "validator"]     # Available tools
memory_scope: isolated                     # Memory isolation level
wait_for:                                  # Dependencies
  docs: ["requirements.md"]
  agents: ["analyst"]
parallel: false                            # Parallel execution flag
format_version: "2.0"                     # Format version (auto-detected)
---

Your agent prompt content goes here...
```

## Field Definitions

### Core Fields

#### `id` (required)
- **Type**: String
- **Pattern**: `^[a-zA-Z][a-zA-Z0-9_-]*$`
- **Description**: Unique agent identifier used throughout the system
- **Examples**: `analyst`, `pm_reviewer`, `qa-specialist`

#### `description` (optional)
- **Type**: String
- **Max Length**: 500 characters
- **Description**: Brief description of agent purpose and role
- **Example**: `"Senior business analyst with expertise in requirements gathering"`

### BMAD Terminology Fields

#### `persona` (optional)
- **Type**: String
- **Max Length**: 200 characters (for token efficiency)
- **Description**: Agent personality and expertise context injected into LLM prompts
- **Example**: `"Senior software architect with 15+ years experience in system design"`
- **Usage**: Automatically prepended to system prompts as role context

#### `tasks` (optional)
- **Type**: Array of strings
- **Pattern**: `^[a-zA-Z0-9_-]+\\.md$`
- **Max Items**: 10
- **Description**: Referenced task definition files that provide structured workflows
- **Example**: `["analyze_requirements.md", "create_stories.md"]`
- **Usage**: Loaded during prep() phase and made available to agent logic

#### `checklists` (optional)
- **Type**: Array of strings  
- **Pattern**: `^[a-zA-Z0-9_-]+\\.md$`
- **Max Items**: 5
- **Description**: Validation checklist files applied in post() phase
- **Example**: `["quality_checklist.md", "completeness_check.md"]`
- **Usage**: Used by supervisor pattern to validate agent outputs

#### `templates` (optional)
- **Type**: Array of strings
- **Pattern**: `^[a-zA-Z0-9_-]+\\.md$` 
- **Max Items**: 5
- **Description**: Output format template files
- **Example**: `["story_template.md", "analysis_report.md"]`
- **Usage**: Loaded and applied during output generation

#### `commands` (optional)
- **Type**: Array of strings
- **Pattern**: `^\\*[a-zA-Z][a-zA-Z0-9_-]*$`
- **Max Items**: 10
- **Description**: Available commands that map to PocketFlow action transitions
- **Example**: `["*analyze", "*validate", "*report"]`
- **Usage**: Commands become action strings for flow control

### Execution Configuration

#### `tools` (optional)
- **Type**: Array of strings
- **Pattern**: `^[a-zA-Z][a-zA-Z0-9_]*$`
- **Max Items**: 10
- **Description**: Tools/utilities available to the agent
- **Example**: `["text_splitter", "validator", "search_engine"]`

#### `memory_scope` (optional, default: "isolated")
- **Type**: String
- **Options**: 
  - `"isolated"`: Agent has private memory
  - `"shared"`: Agent shares memory with all agents  
  - `"shared:namespace"`: Agent shares memory within specific namespace
- **Example**: `"shared:analysis"`

#### `wait_for` (optional)
- **Type**: Object with `docs` and `agents` arrays
- **Description**: Dependencies that must be satisfied before execution
- **Example**: 
  ```yaml
  wait_for:
    docs: ["requirements.md", "constraints.md"]
    agents: ["analyst", "architect"]
  ```

#### `parallel` (optional, default: false)
- **Type**: Boolean
- **Description**: Whether agent can execute in parallel with others

#### `format_version` (auto-detected)
- **Type**: String
- **Options**: `"1.0"`, `"2.0"`
- **Description**: Format version (auto-detected based on BMAD field presence)

## Example Agent Definitions

### 1. Senior Analyst (Full v2.0 Features)

```yaml
---
id: senior_analyst
description: "Senior business analyst for requirements gathering and validation"
persona: "Senior business analyst with 10+ years experience in enterprise software requirements"
tasks: ["analyze_requirements.md", "validate_stories.md"]
checklists: ["quality_checklist.md", "completeness_check.md"]
templates: ["story_template.md", "analysis_report.md"] 
commands: ["*analyze", "*validate", "*report"]
tools: ["text_splitter", "validator"]
memory_scope: "shared:analysis"
wait_for:
  docs: ["requirements.md", "constraints.md"]
  agents: []
parallel: false
---

You are a senior business analyst responsible for analyzing requirements and creating user stories.

Your analysis should be thorough and consider:
- Business value and impact
- Technical feasibility  
- User experience implications
- Integration requirements

Always follow the structured approach defined in your task files and apply quality checklists to ensure completeness.
```

### 2. Project Manager (Supervisor Pattern)

```yaml
---
id: pm_supervisor
description: "Project manager overseeing development workflow quality"
persona: "Experienced project manager with expertise in agile methodologies"
checklists: ["project_quality.md", "deliverable_review.md"]
commands: ["*review", "*approve", "*reject", "*retry"]
tools: ["project_tracker", "quality_validator"]
memory_scope: "shared:project"
wait_for:
  agents: ["senior_analyst", "architect", "developer"]
parallel: false
---

You are a project manager responsible for quality oversight and approval of deliverables.

Review all outputs from the development team against established quality criteria.
Ensure deliverables meet project standards before approving for next phase.
```

### 3. QA Specialist (Validation Focus)

```yaml
---
id: qa_specialist  
description: "Quality assurance specialist for testing and validation"
persona: "QA specialist with expertise in test planning and quality metrics"
tasks: ["create_test_plan.md", "execute_testing.md"]
checklists: ["test_coverage.md", "quality_gates.md"]
templates: ["test_report.md", "bug_report.md"]
commands: ["*plan", "*execute", "*report"]
tools: ["test_framework", "coverage_analyzer"]
memory_scope: "isolated"
parallel: true
---

You are a QA specialist focused on ensuring software quality through comprehensive testing.

Your responsibilities include:
- Creating comprehensive test plans
- Executing test cases systematically  
- Reporting defects with clear reproduction steps
- Validating fixes and regression testing
```

### 4. Software Architect (Design Focus)

```yaml
---
id: software_architect
description: "Senior software architect for system design and technical decisions"
persona: "Software architect with 15+ years experience in distributed systems"
tasks: ["design_architecture.md", "review_technical_specs.md"]
templates: ["architecture_doc.md", "technical_spec.md"]
commands: ["*design", "*review", "*approve"]
tools: ["diagram_generator", "code_analyzer"]
memory_scope: "shared:architecture"
wait_for:
  docs: ["requirements.md", "constraints.md"]
  agents: ["senior_analyst"]
parallel: false
---

You are a senior software architect responsible for system design and technical leadership.

Focus on:
- Scalable and maintainable architecture patterns
- Technology stack recommendations
- Integration strategies and API design
- Performance and security considerations

Ensure all technical decisions are well-documented and aligned with business requirements.
```

### 5. Developer (Implementation Focus)

```yaml
---
id: full_stack_developer
description: "Full-stack developer for feature implementation"
persona: "Full-stack developer with expertise in modern web technologies"
tasks: ["implement_feature.md", "write_tests.md"]
checklists: ["code_quality.md", "test_coverage.md"]
commands: ["*implement", "*test", "*deploy"]
tools: ["code_generator", "test_runner", "linter"]
memory_scope: "isolated"
wait_for:
  agents: ["software_architect"]
parallel: true
---

You are a full-stack developer responsible for implementing features according to specifications.

Your implementation should:
- Follow established coding standards and patterns
- Include comprehensive unit and integration tests
- Meet performance and security requirements
- Be properly documented and maintainable
```

## Migration from v1.0 to v2.0

### Automatic Detection
The parser automatically detects format version based on field presence:
- Files with BMAD terminology fields (`persona`, `tasks`, `checklists`, `templates`, `commands`) are treated as v2.0
- Files without BMAD fields remain v1.0 compatible

### Migration Steps
1. **Add persona**: Define agent role and expertise context
2. **Extract tasks**: Move workflow logic to external task files  
3. **Create checklists**: Define validation criteria as separate files
4. **Design templates**: Create output format templates
5. **Define commands**: Specify available actions for flow control

### Compatibility Notes
- All v1.0 agents continue working without changes
- v2.0 features are additive and optional
- Mixed v1.0/v2.0 agents can coexist in same project
- No breaking changes to existing APIs

## Troubleshooting

### Common Issues

#### Schema Validation Errors
- **Issue**: "Agent ID must be alphanumeric"
- **Fix**: Use only letters, numbers, underscores, and hyphens in `id`

#### File Reference Errors  
- **Issue**: "Task file not found"
- **Fix**: Ensure referenced .md files exist in appropriate directories

#### Memory Scope Issues
- **Issue**: "Invalid memory scope format"  
- **Fix**: Use "isolated", "shared", or "shared:namespace" format

#### Command Format Errors
- **Issue**: "Commands must start with *"
- **Fix**: Prefix all commands with asterisk (e.g., "*analyze")

### Validation Tool
Use the built-in validation tool to check format compliance:

```bash
python scripts/validate_preprocessing.py --src ./preprocessing --schema v2.0
```

## Performance Considerations

- **Persona strings**: Keep under 200 characters for token efficiency
- **File references**: Cached after first load to minimize I/O  
- **Validation**: Checklists applied only after successful execution
- **Generation time**: Maintains <1 second requirement for typical projects

## Next Steps

- See `scripts/validate_preprocessing.py` for validation tooling
- Check `tests/unit/test_preprocessing_v2.py` for comprehensive examples
- Review `docs/preprocessing-v2-mappings.md` for PocketFlow integration details