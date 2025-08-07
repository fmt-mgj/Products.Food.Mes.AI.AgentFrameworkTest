# BMAD to PocketFlow Mapping Specification v2.0

## Overview
This document defines how BMAD methodology concepts map to PocketFlow Node implementations in preprocessing format v2.0.

## Field Mappings

### BMAD Terminology Fields → PocketFlow Properties

| BMAD Field | Type | PocketFlow Usage | Description |
|------------|------|------------------|-------------|
| `persona` | string | Node prompt context | Injected into system prompts to define agent role/expertise |
| `tasks` | list[str] | Referenced files | External .md files containing structured task definitions |
| `checklists` | list[str] | Referenced files | External .md files containing validation/quality checklists |
| `templates` | list[str] | Referenced files | External .md files containing output format templates |
| `commands` | list[str] | Action mappings | Available actions that map to Flow transitions |

### PocketFlow Pattern Mappings

Based on cookbook analysis:

#### 1. Stateless Execution Pattern
- **Source**: `pocketflow-structured-output/`
- **Usage**: All agents use prep/exec/post lifecycle
- **Mapping**: 
  - `prep()`: Load referenced files (tasks, checklists, templates)
  - `exec()`: Apply persona context + execute core logic
  - `post()`: Validate output against checklists

#### 2. External Control Pattern  
- **Source**: `pocketflow-communication/`
- **Usage**: Flow transitions based on external input
- **Mapping**: 
  - `commands` → Flow action strings
  - User interactions trigger specific command flows

#### 3. Validation Pattern
- **Source**: `pocketflow-supervisor/`
- **Usage**: Quality assurance via checklists
- **Mapping**: 
  - `checklists` → Supervisor node validation
  - Failed validation triggers retry with feedback

### Code Generation Templates

#### Node Class Structure
```python
class {AgentID}Node(Node):
    def prep(self, shared):
        context = {
            "persona": "{persona}",
            "tasks": self.load_references({tasks}),
            "checklists": self.load_references({checklists}),
            "templates": self.load_references({templates})
        }
        return context
    
    def exec(self, prep_res):
        # Apply persona context to prompt
        system_prompt = f"You are {prep_res['persona']}..."
        # Execute with task guidance
        return call_llm(system_prompt + prompt)
    
    def post(self, shared, prep_res, exec_res):
        # Validate against checklists if provided
        if prep_res.get('checklists'):
            validate_output(exec_res, prep_res['checklists'])
        
        shared['{agent_id}_result'] = exec_res
        return "success"  # or specific command from self.commands
```

#### Flow Transitions
```python
# Commands map to flow actions
{agent_id}_node - "{command1}" >> next_node1
{agent_id}_node - "{command2}" >> next_node2
```

### Implementation Notes

1. **File Loading**: Referenced files loaded lazily during prep() phase
2. **Persona Injection**: Added as system context in all LLM calls
3. **Validation**: Checklists applied in post() phase for quality assurance
4. **Commands**: Map directly to PocketFlow action strings for flow control
5. **Backward Compatibility**: v1.0 format generates same Node structure without BMAD fields

### Performance Considerations

- File references cached after first load
- Persona strings kept short (< 200 chars) for token efficiency  
- Checklists applied only on successful exec() completion
- Template expansion deferred until actual usage

## Next Steps

This mapping will be implemented in:
- `scripts/generator.py`: Code generation logic
- `scripts/templates/agent_v2.py.j2`: Enhanced Jinja2 template
- `tests/unit/test_mappings.py`: Validation tests