"""Configuration Loader for BMAD Workflow and Tools.

This module loads optional workflow.yaml and tools.yaml configuration files
for agent orchestration and tool registration, following KISS principles.
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

import yaml

logger = logging.getLogger(__name__)


class ConfigurationError(Exception):
    """Raised when configuration loading or validation fails."""
    pass


class WorkflowConfig:
    """Container for workflow configuration."""

    def __init__(self, flows: Optional[Dict[str, Dict[str, Any]]] = None):
        self.flows = flows or {}


class ToolConfig:
    """Container for tool configuration."""

    def __init__(self, tools: Optional[Dict[str, Dict[str, Any]]] = None):
        self.tools = tools or {}


def _load_yaml_file(file_path: Path, file_type: str) -> Dict[str, Any]:
    """Helper function to load and parse YAML files.

    Args:
        file_path: Path to YAML file.
        file_type: Type of file (for error messages).

    Returns:
        Parsed YAML data as dictionary.

    Raises:
        ConfigurationError: If YAML parsing fails.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f) or {}
    except yaml.YAMLError as e:
        logger.error(f"Failed to parse {file_type} YAML from {file_path}: {e}")
        raise ConfigurationError(f"Invalid YAML in {file_type} file {file_path}: {e}")
    except Exception as e:
        logger.error(f"Failed to load {file_type} from {file_path}: {e}")
        raise


def load_workflow(workflow_path: Path) -> WorkflowConfig:
    """Load workflow configuration from YAML file.

    Args:
        workflow_path: Path to workflow YAML file (typically workflows/default.yaml).

    Returns:
        WorkflowConfig object with flow definitions.

    Raises:
        ConfigurationError: If YAML parsing fails.
    """
    if not workflow_path.exists():
        logger.info(
            f"Workflow file not found at {workflow_path}, using empty configuration"
        )
        return WorkflowConfig()

    data = _load_yaml_file(workflow_path, "workflow")
    flows = data.get('flows', {})

    # Basic structure validation
    for flow_name, flow_def in flows.items():
        if 'steps' not in flow_def:
            logger.warning(f"Flow '{flow_name}' missing 'steps' definition, skipping")
            continue

        # Ensure each step has agents list
        for i, step in enumerate(flow_def['steps']):
            if 'agents' not in step:
                logger.warning(
                    f"Flow '{flow_name}' step {i} missing 'agents', skipping"
                )

    logger.info(f"Loaded {len(flows)} workflow flows from {workflow_path}")
    return WorkflowConfig(flows=flows)


def load_tools(tools_path: Path) -> ToolConfig:
    """Load tools configuration from YAML file.

    Args:
        tools_path: Path to tools YAML file (typically bmad/tools.yaml).

    Returns:
        ToolConfig object with tool definitions.

    Raises:
        ConfigurationError: If YAML parsing fails.
    """
    if not tools_path.exists():
        logger.info(f"Tools file not found at {tools_path}, using empty configuration")
        return ToolConfig()

    data = _load_yaml_file(tools_path, "tools")
    tools = data.get('tools', {})

    # Basic structure validation
    for tool_name, tool_def in tools.items():
        if 'module' not in tool_def:
            logger.warning(f"Tool '{tool_name}' missing 'module', skipping")
            continue
        if 'function' not in tool_def:
            logger.warning(f"Tool '{tool_name}' missing 'function', skipping")
            continue

    logger.info(f"Loaded {len(tools)} tool definitions from {tools_path}")
    return ToolConfig(tools=tools)


def merge_configurations(agent_metadata: Dict, workflow_config: WorkflowConfig,
                        tool_config: ToolConfig) -> Dict:
    """Merge workflow and tool configurations with agent metadata.

    Front-matter from agent files takes precedence over workflow/tool configs.

    Args:
        agent_metadata: Dictionary of agent metadata from parser.
        workflow_config: Workflow configuration.
        tool_config: Tool configuration.

    Returns:
        Merged configuration dictionary.
    """
    merged = {
        'agents': agent_metadata,
        'workflows': workflow_config.flows,
        'tools': tool_config.tools
    }

    # Apply workflow configurations to agents if not overridden
    for flow_name, flow_def in workflow_config.flows.items():
        for step in flow_def.get('steps', []):
            agent_names = step.get('agents', [])

            # Mark agents in parallel steps
            if len(agent_names) > 1:
                for agent_name in agent_names:
                    if agent_name in agent_metadata:
                        agent = agent_metadata[agent_name][0]
                        # Only set parallel if not already defined in front-matter
                        if not hasattr(agent, '_front_matter_parallel'):
                            agent.parallel = True

    logger.info(
        f"Merged configuration with {len(agent_metadata)} agents, "
        f"{len(workflow_config.flows)} workflows, {len(tool_config.tools)} tools"
    )

    return merged


def validate_configuration(config: Dict) -> List[str]:
    """Validate the merged configuration for consistency.

    Args:
        config: Merged configuration dictionary.

    Returns:
        List of validation error messages (empty if valid).
    """
    errors = []
    agents = config.get('agents', {})
    workflows = config.get('workflows', {})
    tools = config.get('tools', {})

    # Create sets for efficient lookups
    agent_ids = set(agents.keys())
    tool_ids = set(tools.keys())

    # Validate workflow references
    for flow_name, flow_def in workflows.items():
        for i, step in enumerate(flow_def.get('steps', [])):
            for agent_name in step.get('agents', []):
                if agent_name not in agent_ids:
                    errors.append(f"Workflow '{flow_name}' step {i} references "
                                f"non-existent agent '{agent_name}'")

    # Validate agent tool references
    for agent_id, (metadata, _) in agents.items():
        for tool_name in metadata.tools:
            if tool_name not in tool_ids:
                errors.append(
                    f"Agent '{agent_id}' references non-existent tool '{tool_name}'"
                )

    # Validate agent dependencies
    for agent_id, (metadata, _) in agents.items():
        for dep_agent in metadata.wait_for.get('agents', []):
            if dep_agent not in agent_ids:
                errors.append(
                    f"Agent '{agent_id}' depends on non-existent agent '{dep_agent}'"
                )

    # Check for circular dependencies in workflows
    for flow_name, flow_def in workflows.items():
        seen_agents: Set[str] = set()
        for step in flow_def.get('steps', []):
            step_agents = set(step.get('agents', []))
            duplicates = step_agents & seen_agents
            if duplicates:
                errors.append(
                    f"Workflow '{flow_name}' has potential circular dependency: "
                    f"agents {duplicates} appear multiple times"
                )
            seen_agents.update(step_agents)

    # Validate tool module paths
    for tool_name, tool_def in tools.items():
        module = tool_def.get('module', '')
        function = tool_def.get('function', '')

        if not module:
            errors.append(f"Tool '{tool_name}' missing module path")
        if not function:
            errors.append(f"Tool '{tool_name}' missing function name")

        # Basic Python module path validation
        if module and not all(part.isidentifier() for part in module.split('.')):
            errors.append(f"Tool '{tool_name}' has invalid module path: {module}")
        if function and not function.isidentifier():
            errors.append(f"Tool '{tool_name}' has invalid function name: {function}")

    if errors:
        logger.error(f"Configuration validation found {len(errors)} errors")
    else:
        logger.info("Configuration validation passed")

    return errors


def load_all_configurations(bmad_dir: Path, agents_dict: Dict) -> Dict:
    """Load all configurations and merge with agent metadata.

    Args:
        bmad_dir: Root BMAD directory containing agents/, workflows/, tools.yaml.
        agents_dict: Dictionary of agent metadata from parser.

    Returns:
        Merged and validated configuration dictionary.

    Raises:
        ValueError: If configuration is invalid.
    """
    # Define paths
    workflows_dir = bmad_dir / 'workflows'
    default_workflow = workflows_dir / 'default.yaml'
    tools_file = bmad_dir / 'tools.yaml'

    # Load configurations
    workflow_config = load_workflow(default_workflow)
    tool_config = load_tools(tools_file)

    # Merge configurations
    merged = merge_configurations(agents_dict, workflow_config, tool_config)

    # Validate
    errors = validate_configuration(merged)
    if errors:
        error_msg = '\n'.join(errors)
        raise ConfigurationError(f"Configuration validation failed:\n{error_msg}")

    return merged
