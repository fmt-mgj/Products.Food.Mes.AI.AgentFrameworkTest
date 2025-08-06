"""Unit tests for configuration loader module."""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
import yaml

from scripts.config_loader import (
    WorkflowConfig,
    ToolConfig,
    ConfigurationError,
    load_workflow,
    load_tools,
    merge_configurations,
    validate_configuration,
    load_all_configurations
)
from scripts.parser import AgentMetadata


class TestWorkflowLoader:
    """Test workflow.yaml loading functionality."""
    
    def test_load_workflow_valid(self, tmp_path):
        """Test loading a valid workflow configuration."""
        workflow_file = tmp_path / "default.yaml"
        workflow_data = {
            'flows': {
                'default': {
                    'steps': [
                        {'agents': ['analyst']},
                        {'agents': ['architect', 'reviewer']},
                        {'agents': ['tester']}
                    ]
                }
            }
        }
        
        with open(workflow_file, 'w') as f:
            yaml.dump(workflow_data, f)
        
        config = load_workflow(workflow_file)
        
        assert isinstance(config, WorkflowConfig)
        assert 'default' in config.flows
        assert len(config.flows['default']['steps']) == 3
        assert config.flows['default']['steps'][1]['agents'] == ['architect', 'reviewer']
    
    def test_load_workflow_missing_file(self, tmp_path):
        """Test graceful handling of missing workflow file."""
        missing_file = tmp_path / "missing.yaml"
        
        config = load_workflow(missing_file)
        
        assert isinstance(config, WorkflowConfig)
        assert config.flows == {}
    
    def test_load_workflow_empty_file(self, tmp_path):
        """Test loading empty workflow file."""
        empty_file = tmp_path / "empty.yaml"
        empty_file.touch()
        
        config = load_workflow(empty_file)
        
        assert isinstance(config, WorkflowConfig)
        assert config.flows == {}
    
    def test_load_workflow_invalid_yaml(self, tmp_path):
        """Test handling of invalid YAML syntax."""
        invalid_file = tmp_path / "invalid.yaml"
        
        with open(invalid_file, 'w') as f:
            f.write("flows:\n  - invalid: [unclosed")
        
        with pytest.raises(ConfigurationError, match="Invalid YAML"):
            load_workflow(invalid_file)
    
    def test_load_workflow_missing_steps(self, tmp_path, caplog):
        """Test warning for flows missing steps."""
        workflow_file = tmp_path / "nosteps.yaml"
        workflow_data = {
            'flows': {
                'incomplete': {
                    'name': 'Test Flow'
                }
            }
        }
        
        with open(workflow_file, 'w') as f:
            yaml.dump(workflow_data, f)
        
        config = load_workflow(workflow_file)
        
        assert "missing 'steps' definition" in caplog.text
        assert isinstance(config, WorkflowConfig)


class TestToolsLoader:
    """Test tools.yaml loading functionality."""
    
    def test_load_tools_valid(self, tmp_path):
        """Test loading a valid tools configuration."""
        tools_file = tmp_path / "tools.yaml"
        tools_data = {
            'tools': {
                'search': {
                    'module': 'utils.search',
                    'function': 'perform_search',
                    'description': 'Search for information'
                },
                'write_doc': {
                    'module': 'utils.documents',
                    'function': 'write_document',
                    'description': 'Write a document'
                }
            }
        }
        
        with open(tools_file, 'w') as f:
            yaml.dump(tools_data, f)
        
        config = load_tools(tools_file)
        
        assert isinstance(config, ToolConfig)
        assert 'search' in config.tools
        assert 'write_doc' in config.tools
        assert config.tools['search']['module'] == 'utils.search'
        assert config.tools['search']['function'] == 'perform_search'
    
    def test_load_tools_missing_file(self, tmp_path):
        """Test graceful handling of missing tools file."""
        missing_file = tmp_path / "missing.yaml"
        
        config = load_tools(missing_file)
        
        assert isinstance(config, ToolConfig)
        assert config.tools == {}
    
    def test_load_tools_empty_file(self, tmp_path):
        """Test loading empty tools file."""
        empty_file = tmp_path / "empty.yaml"
        empty_file.touch()
        
        config = load_tools(empty_file)
        
        assert isinstance(config, ToolConfig)
        assert config.tools == {}
    
    def test_load_tools_invalid_yaml(self, tmp_path):
        """Test handling of invalid YAML syntax."""
        invalid_file = tmp_path / "invalid.yaml"
        
        with open(invalid_file, 'w') as f:
            f.write("tools:\n  search: {module: [invalid")
        
        with pytest.raises(ConfigurationError, match="Invalid YAML"):
            load_tools(invalid_file)
    
    def test_load_tools_missing_fields(self, tmp_path, caplog):
        """Test warnings for tools missing required fields."""
        tools_file = tmp_path / "incomplete.yaml"
        tools_data = {
            'tools': {
                'no_module': {
                    'function': 'test_func'
                },
                'no_function': {
                    'module': 'test.module'
                }
            }
        }
        
        with open(tools_file, 'w') as f:
            yaml.dump(tools_data, f)
        
        config = load_tools(tools_file)
        
        assert "missing 'module'" in caplog.text
        assert "missing 'function'" in caplog.text
        assert isinstance(config, ToolConfig)


class TestConfigurationMerging:
    """Test configuration merging functionality."""
    
    def test_merge_configurations_basic(self):
        """Test basic configuration merging."""
        agent1 = AgentMetadata(id='agent1', tools=['tool1'])
        agent2 = AgentMetadata(id='agent2', memory_scope='shared')
        agents_dict = {
            'agent1': (agent1, 'Agent 1 prompt'),
            'agent2': (agent2, 'Agent 2 prompt')
        }
        
        workflow_config = WorkflowConfig(flows={'test': {'steps': []}})
        tool_config = ToolConfig(tools={'tool1': {'module': 'test', 'function': 'func'}})
        
        merged = merge_configurations(agents_dict, workflow_config, tool_config)
        
        assert 'agents' in merged
        assert 'workflows' in merged
        assert 'tools' in merged
        assert merged['agents'] == agents_dict
        assert merged['workflows'] == workflow_config.flows
        assert merged['tools'] == tool_config.tools
    
    def test_merge_configurations_parallel_marking(self):
        """Test that parallel agents are marked correctly."""
        agent1 = AgentMetadata(id='agent1')
        agent2 = AgentMetadata(id='agent2')
        agents_dict = {
            'agent1': (agent1, 'prompt1'),
            'agent2': (agent2, 'prompt2')
        }
        
        workflow_config = WorkflowConfig(flows={
            'test': {
                'steps': [
                    {'agents': ['agent1', 'agent2']}  # Parallel step
                ]
            }
        })
        tool_config = ToolConfig()
        
        merged = merge_configurations(agents_dict, workflow_config, tool_config)
        
        assert agent1.parallel == True
        assert agent2.parallel == True
    
    def test_merge_configurations_preserves_frontmatter(self):
        """Test that front-matter values are preserved."""
        agent1 = AgentMetadata(id='agent1', parallel=False)
        agent1._front_matter_parallel = True  # Simulate front-matter setting
        
        agents_dict = {'agent1': (agent1, 'prompt')}
        
        workflow_config = WorkflowConfig(flows={
            'test': {
                'steps': [
                    {'agents': ['agent1', 'other']}  # Would normally set parallel=True
                ]
            }
        })
        tool_config = ToolConfig()
        
        merged = merge_configurations(agents_dict, workflow_config, tool_config)
        
        # Should remain False because front-matter takes precedence
        assert agent1.parallel == False


class TestConfigurationValidation:
    """Test configuration validation functionality."""
    
    def test_validate_configuration_valid(self):
        """Test validation of a valid configuration."""
        agent1 = AgentMetadata(id='agent1', tools=['tool1'])
        config = {
            'agents': {'agent1': (agent1, 'prompt')},
            'workflows': {
                'test': {'steps': [{'agents': ['agent1']}]}
            },
            'tools': {
                'tool1': {'module': 'utils.test', 'function': 'test_func'}
            }
        }
        
        errors = validate_configuration(config)
        
        assert errors == []
    
    def test_validate_configuration_missing_agent(self):
        """Test validation catches missing agent references."""
        config = {
            'agents': {},
            'workflows': {
                'test': {'steps': [{'agents': ['missing_agent']}]}
            },
            'tools': {}
        }
        
        errors = validate_configuration(config)
        
        assert len(errors) == 1
        assert 'non-existent agent' in errors[0]
        assert 'missing_agent' in errors[0]
    
    def test_validate_configuration_missing_tool(self):
        """Test validation catches missing tool references."""
        agent1 = AgentMetadata(id='agent1', tools=['missing_tool'])
        config = {
            'agents': {'agent1': (agent1, 'prompt')},
            'workflows': {},
            'tools': {}
        }
        
        errors = validate_configuration(config)
        
        assert len(errors) == 1
        assert 'non-existent tool' in errors[0]
        assert 'missing_tool' in errors[0]
    
    def test_validate_configuration_missing_dependency(self):
        """Test validation catches missing agent dependencies."""
        agent1 = AgentMetadata(
            id='agent1',
            wait_for={'agents': ['missing_dep'], 'docs': []}
        )
        config = {
            'agents': {'agent1': (agent1, 'prompt')},
            'workflows': {},
            'tools': {}
        }
        
        errors = validate_configuration(config)
        
        assert len(errors) == 1
        assert 'non-existent agent' in errors[0]
        assert 'missing_dep' in errors[0]
    
    def test_validate_configuration_circular_dependency(self):
        """Test validation catches potential circular dependencies."""
        agent1 = AgentMetadata(id='agent1')
        config = {
            'agents': {'agent1': (agent1, 'prompt')},
            'workflows': {
                'test': {
                    'steps': [
                        {'agents': ['agent1']},
                        {'agents': ['agent1']}  # Same agent appears twice
                    ]
                }
            },
            'tools': {}
        }
        
        errors = validate_configuration(config)
        
        assert len(errors) == 1
        assert 'circular dependency' in errors[0]
    
    def test_validate_configuration_invalid_tool_paths(self):
        """Test validation of tool module and function names."""
        config = {
            'agents': {},
            'workflows': {},
            'tools': {
                'bad_module': {'module': '123invalid', 'function': 'test'},
                'bad_function': {'module': 'valid.module', 'function': '456-bad'},
                'missing_module': {'function': 'test'},
                'missing_function': {'module': 'test'}
            }
        }
        
        errors = validate_configuration(config)
        
        assert len(errors) >= 4
        error_text = '\n'.join(errors)
        assert 'invalid module path' in error_text
        assert 'invalid function name' in error_text
        assert 'missing module' in error_text
        assert 'missing function' in error_text


class TestLoadAllConfigurations:
    """Test the main configuration loading function."""
    
    def test_load_all_configurations_success(self, tmp_path):
        """Test successful loading of all configurations."""
        # Create directory structure
        bmad_dir = tmp_path / 'bmad'
        workflows_dir = bmad_dir / 'workflows'
        workflows_dir.mkdir(parents=True)
        
        # Create workflow file
        workflow_file = workflows_dir / 'default.yaml'
        with open(workflow_file, 'w') as f:
            yaml.dump({
                'flows': {
                    'default': {
                        'steps': [{'agents': ['agent1']}]
                    }
                }
            }, f)
        
        # Create tools file
        tools_file = bmad_dir / 'tools.yaml'
        with open(tools_file, 'w') as f:
            yaml.dump({
                'tools': {
                    'tool1': {
                        'module': 'utils.test',
                        'function': 'test_func'
                    }
                }
            }, f)
        
        # Create agent metadata
        agent1 = AgentMetadata(id='agent1', tools=['tool1'])
        agents_dict = {'agent1': (agent1, 'prompt')}
        
        # Load all configurations
        config = load_all_configurations(bmad_dir, agents_dict)
        
        assert 'agents' in config
        assert 'workflows' in config
        assert 'tools' in config
        assert config['agents'] == agents_dict
        assert 'default' in config['workflows']
        assert 'tool1' in config['tools']
    
    def test_load_all_configurations_validation_error(self, tmp_path):
        """Test that validation errors are raised."""
        # Create directory structure
        bmad_dir = tmp_path / 'bmad'
        workflows_dir = bmad_dir / 'workflows'
        workflows_dir.mkdir(parents=True)
        
        # Create workflow with invalid agent reference
        workflow_file = workflows_dir / 'default.yaml'
        with open(workflow_file, 'w') as f:
            yaml.dump({
                'flows': {
                    'default': {
                        'steps': [{'agents': ['missing_agent']}]
                    }
                }
            }, f)
        
        # Empty agent dict
        agents_dict = {}
        
        # Should raise validation error
        with pytest.raises(ConfigurationError, match="Configuration validation failed"):
            load_all_configurations(bmad_dir, agents_dict)
    
    def test_load_all_configurations_missing_files(self, tmp_path):
        """Test that missing files are handled gracefully."""
        # Create only the bmad directory
        bmad_dir = tmp_path / 'bmad'
        bmad_dir.mkdir()
        
        # Create agent metadata
        agent1 = AgentMetadata(id='agent1')
        agents_dict = {'agent1': (agent1, 'prompt')}
        
        # Should work with empty configurations
        config = load_all_configurations(bmad_dir, agents_dict)
        
        assert config['agents'] == agents_dict
        assert config['workflows'] == {}
        assert config['tools'] == {}