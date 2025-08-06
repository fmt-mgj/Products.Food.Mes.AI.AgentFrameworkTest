"""Unit tests for executor dependency validation."""

import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch
import yaml

from generated.executor import (
    DependencyChecker, 
    DependencyResult, 
    DependencyError, 
    CircularDependencyError,
    FlowExecutor
)
from generated.memory import MemoryManager


class TestDependencyChecker:
    """Test dependency checking functionality."""
    
    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.docs_dir = self.temp_dir / "docs"
        self.docs_dir.mkdir()
        self.checker = DependencyChecker(self.docs_dir)
    
    def teardown_method(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir)
    
    def test_check_document_dependencies_all_exist_returns_empty_list(self):
        """Test that all existing documents return empty missing list."""
        # Arrange
        (self.docs_dir / "doc1.md").touch()
        (self.docs_dir / "doc2.md").touch()
        required_docs = ["doc1", "doc2"]
        
        # Act
        missing = self.checker.check_document_dependencies(required_docs)
        
        # Assert
        assert missing == []
    
    def test_check_document_dependencies_missing_docs_returns_list(self):
        """Test that missing documents are returned in list."""
        # Arrange
        (self.docs_dir / "doc1.md").touch()
        required_docs = ["doc1", "doc2", "doc3"]
        
        # Act
        missing = self.checker.check_document_dependencies(required_docs)
        
        # Assert
        assert missing == ["doc2", "doc3"]
    
    def test_check_agent_dependencies_all_completed_returns_empty(self):
        """Test that all completed agents return empty missing list."""
        # Arrange
        required_agents = ["agent1", "agent2"]
        completed_agents = ["agent1", "agent2", "agent3"]
        
        # Act
        missing = self.checker.check_agent_dependencies(required_agents, completed_agents)
        
        # Assert
        assert missing == []
    
    def test_check_agent_dependencies_missing_agents_returns_list(self):
        """Test that missing agents are returned in list."""
        # Arrange
        required_agents = ["agent1", "agent2", "agent3"]
        completed_agents = ["agent1"]
        
        # Act
        missing = self.checker.check_agent_dependencies(required_agents, completed_agents)
        
        # Assert
        assert missing == ["agent2", "agent3"]
    
    def test_check_dependencies_returns_combined_result(self):
        """Test that check_dependencies returns both missing docs and agents."""
        # Arrange
        (self.docs_dir / "doc1.md").touch()
        agent_metadata = {
            "wait_for": {
                "docs": ["doc1", "doc2"],
                "agents": ["agent1", "agent2"]
            }
        }
        completed_agents = ["agent1"]
        
        # Act
        result = self.checker.check_dependencies(agent_metadata, completed_agents)
        
        # Assert
        assert result.missing_docs == ["doc2"]
        assert result.missing_agents == ["agent2"]
    
    def test_circular_dependency_detection_raises_error(self):
        """Test that circular dependencies are detected and raise error."""
        # Arrange
        agents_metadata = {
            "agent1": {"wait_for": {"agents": ["agent2"]}},
            "agent2": {"wait_for": {"agents": ["agent3"]}},
            "agent3": {"wait_for": {"agents": ["agent1"]}}
        }
        
        # Act & Assert
        with pytest.raises(CircularDependencyError) as exc_info:
            self.checker.detect_circular_dependencies(agents_metadata)
        
        assert "Circular dependency detected" in str(exc_info.value)
        assert "agent1" in str(exc_info.value)
    
    def test_circular_dependency_detection_no_cycle_passes(self):
        """Test that non-circular dependencies pass validation."""
        # Arrange
        agents_metadata = {
            "agent1": {"wait_for": {"agents": ["agent2"]}},
            "agent2": {"wait_for": {"agents": ["agent3"]}},
            "agent3": {"wait_for": {"agents": []}}
        }
        
        # Act & Assert (should not raise)
        self.checker.detect_circular_dependencies(agents_metadata)
    
    def test_dependency_graph_generation_returns_valid_json(self):
        """Test that dependency graph is generated correctly."""
        # Arrange
        agents_metadata = {
            "agent1": {"wait_for": {"docs": ["doc1"], "agents": ["agent2"]}},
            "agent2": {"wait_for": {"docs": [], "agents": []}}
        }
        
        # Act
        graph = self.checker.get_dependency_graph(agents_metadata)
        
        # Assert
        expected = {
            "agent1": {"docs": ["doc1"], "agents": ["agent2"]},
            "agent2": {"docs": [], "agents": []}
        }
        assert graph == expected


class TestFlowExecutor:
    """Test flow executor functionality."""
    
    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.memory_manager = Mock(spec=MemoryManager)
    
    def teardown_method(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir)
    
    @patch('generated.executor.FlowExecutor._load_agents')
    @patch('generated.executor.FlowExecutor._load_agents_metadata')
    @patch('generated.executor.FlowExecutor._load_runtime_config')
    @patch('generated.executor.DependencyChecker.detect_circular_dependencies')
    def test_execute_agent_with_missing_docs_wait_returns_pending(self, mock_circular, mock_config, mock_metadata, mock_agents):
        """Test that missing documents with 'wait' config returns pending_docs."""
        # Arrange
        mock_agents.return_value = {}
        mock_metadata.return_value = {"agent1": {"wait_for": {"docs": ["doc1"], "agents": []}}}
        mock_config.return_value = {"on_missing_doc": "wait"}
        mock_circular.return_value = None
        
        with patch.object(DependencyChecker, 'check_document_dependencies', return_value=["doc1"]):
            executor = FlowExecutor(self.memory_manager)
            
            # Act
            can_execute, dep_result = executor.check_agent_dependencies("agent1", [])
            
            # Assert
            assert not can_execute
            assert dep_result.missing_docs == ["doc1"]
    
    @patch('generated.executor.FlowExecutor._load_agents')
    @patch('generated.executor.FlowExecutor._load_agents_metadata')
    @patch('generated.executor.FlowExecutor._load_runtime_config')
    @patch('generated.executor.DependencyChecker.detect_circular_dependencies')
    def test_execute_agent_with_missing_docs_skip_continues(self, mock_circular, mock_config, mock_metadata, mock_agents):
        """Test that missing documents with 'skip' config skips execution."""
        # Arrange
        mock_agents.return_value = {}
        mock_metadata.return_value = {"agent1": {"wait_for": {"docs": ["doc1"], "agents": []}}}
        mock_config.return_value = {"on_missing_doc": "skip"}
        mock_circular.return_value = None
        
        with patch.object(DependencyChecker, 'check_document_dependencies', return_value=["doc1"]):
            executor = FlowExecutor(self.memory_manager)
            
            # Act
            can_execute, dep_result = executor.check_agent_dependencies("agent1", [])
            
            # Assert
            assert not can_execute
            assert dep_result.missing_docs == ["doc1"]
    
    @patch('generated.executor.FlowExecutor._load_agents')
    @patch('generated.executor.FlowExecutor._load_agents_metadata')
    @patch('generated.executor.FlowExecutor._load_runtime_config')
    @patch('generated.executor.DependencyChecker.detect_circular_dependencies')
    def test_execute_agent_with_missing_docs_error_raises_exception(self, mock_circular, mock_config, mock_metadata, mock_agents):
        """Test that missing documents with 'error' config raises exception."""
        # Arrange
        mock_agents.return_value = {}
        mock_metadata.return_value = {"agent1": {"wait_for": {"docs": ["doc1"], "agents": []}}}
        mock_config.return_value = {"on_missing_doc": "error"}
        mock_circular.return_value = None
        
        with patch.object(DependencyChecker, 'check_document_dependencies', return_value=["doc1"]):
            executor = FlowExecutor(self.memory_manager)
            
            # Act & Assert
            with pytest.raises(DependencyError) as exc_info:
                executor.check_agent_dependencies("agent1", [])
            
            assert "Missing dependencies for agent1" in str(exc_info.value)
    
    @patch('generated.executor.FlowExecutor._load_agents')
    @patch('generated.executor.FlowExecutor._load_agents_metadata')
    @patch('generated.executor.FlowExecutor._load_runtime_config')
    @patch('generated.executor.DependencyChecker.detect_circular_dependencies')
    def test_execute_agent_no_metadata_returns_true(self, mock_circular, mock_config, mock_metadata, mock_agents):
        """Test that agents without metadata can execute normally."""
        # Arrange
        mock_agents.return_value = {}
        mock_metadata.return_value = {}
        mock_config.return_value = {"on_missing_doc": "skip"}
        mock_circular.return_value = None
        
        executor = FlowExecutor(self.memory_manager)
        
        # Act
        can_execute, dep_result = executor.check_agent_dependencies("agent1", [])
        
        # Assert
        assert can_execute
        assert dep_result.missing_docs == []
        assert dep_result.missing_agents == []
    
    @patch('generated.executor.FlowExecutor._load_agents')
    @patch('generated.executor.FlowExecutor._load_agents_metadata')
    @patch('generated.executor.FlowExecutor._load_runtime_config')
    @patch('generated.executor.DependencyChecker.detect_circular_dependencies')
    def test_execute_agent_with_satisfied_dependencies_returns_true(self, mock_circular, mock_config, mock_metadata, mock_agents):
        """Test that agents with satisfied dependencies can execute."""
        # Arrange
        mock_agents.return_value = {}
        mock_metadata.return_value = {"agent1": {"wait_for": {"docs": ["doc1"], "agents": ["agent2"]}}}
        mock_config.return_value = {"on_missing_doc": "wait"}
        mock_circular.return_value = None
        
        with patch.object(DependencyChecker, 'check_document_dependencies', return_value=[]), \
             patch.object(DependencyChecker, 'check_agent_dependencies', return_value=[]):
            executor = FlowExecutor(self.memory_manager)
            
            # Act
            can_execute, dep_result = executor.check_agent_dependencies("agent1", ["agent2"])
            
            # Assert
            assert can_execute
            assert dep_result.missing_docs == []
            assert dep_result.missing_agents == []


class TestEdgeCases:
    """Test edge cases and error conditions."""
    
    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.docs_dir = self.temp_dir / "docs"
        self.docs_dir.mkdir()
        self.checker = DependencyChecker(self.docs_dir)
    
    def teardown_method(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir)
    
    def test_empty_dependencies_returns_empty_lists(self):
        """Test that empty dependency lists work correctly."""
        # Arrange
        agent_metadata = {"wait_for": {"docs": [], "agents": []}}
        
        # Act
        result = self.checker.check_dependencies(agent_metadata, [])
        
        # Assert
        assert result.missing_docs == []
        assert result.missing_agents == []
    
    def test_missing_wait_for_key_returns_empty_lists(self):
        """Test that missing wait_for key works correctly."""
        # Arrange
        agent_metadata = {}
        
        # Act
        result = self.checker.check_dependencies(agent_metadata, [])
        
        # Assert
        assert result.missing_docs == []
        assert result.missing_agents == []
    
    def test_self_dependency_detection(self):
        """Test that self-dependencies are handled correctly."""
        # Arrange
        agents_metadata = {
            "agent1": {"wait_for": {"agents": ["agent1"]}}
        }
        
        # Act & Assert
        with pytest.raises(CircularDependencyError):
            self.checker.detect_circular_dependencies(agents_metadata)
    
    def test_invalid_document_paths_handled_gracefully(self):
        """Test that invalid document paths don't crash the system."""
        # Arrange
        required_docs = ["../invalid", "doc with spaces", "doc/with/slashes"]
        
        # Act
        missing = self.checker.check_document_dependencies(required_docs)
        
        # Assert
        assert len(missing) == 3  # All should be missing since they don't exist