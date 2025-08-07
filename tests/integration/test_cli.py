"""Integration tests for the BMAD to PocketFlow CLI tool.

Tests the complete end-to-end generation pipeline through the CLI interface.
"""

import ast
import os
import subprocess
import tempfile
import time
from pathlib import Path

import pytest


class TestCLIIntegration:
    """Test the bmad2pf CLI tool end-to-end."""

    def test_cli_help_command(self):
        """Test that --help flag works correctly."""
        result = subprocess.run(
            ["python", "scripts/bmad2pf.py", "--help"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent
        )
        
        assert result.returncode == 0
        assert "bmad2pf" in result.stdout
        assert "Convert BMAD artifacts to PocketFlow code" in result.stdout
        assert "--src" in result.stdout
        assert "--out" in result.stdout
        assert "--verbose" in result.stdout

    def test_cli_missing_source_directory(self):
        """Test CLI behavior when source directory doesn't exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            non_existent_path = Path(temp_dir) / "non_existent"
            
            result = subprocess.run(
                ["python", "scripts/bmad2pf.py", "--src", str(non_existent_path)],
                capture_output=True,
                text=True,
                cwd=Path(__file__).parent.parent.parent
            )
            
            assert result.returncode == 5  # File not found error
            assert "Source directory does not exist" in result.stderr

    def test_cli_successful_generation(self):
        """Test complete successful generation pipeline."""
        project_root = Path(__file__).parent.parent.parent
        fixtures_path = project_root / "tests" / "fixtures" / "sample_agents"
        
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "generated"
            
            # Measure execution time
            start_time = time.perf_counter()
            
            result = subprocess.run([
                "python", "scripts/bmad2pf.py",
                "--src", str(fixtures_path),
                "--out", str(output_path)
            ], capture_output=True, text=True, cwd=project_root)
            
            end_time = time.perf_counter()
            execution_time = end_time - start_time
            
            # Check successful execution
            assert result.returncode == 0, f"CLI failed with error: {result.stderr}"
            
            # Check timing requirement (< 2 seconds including subprocess overhead)
            # Note: The actual generation time reported by the tool should be < 1.0s
            assert execution_time < 2.0, f"Total execution took {execution_time:.3f}s, expected < 2.0s with subprocess overhead"
            
            # Verify the tool reports generation time < 1.0s
            assert "[SUCCESS] Generation complete in" in result.stdout
            # Extract the reported time from output
            for line in result.stdout.split('\n'):
                if "[SUCCESS] Generation complete in" in line:
                    time_str = line.split("in ")[1].split("s")[0]
                    reported_time = float(time_str)
                    assert reported_time < 1.0, f"Reported generation time {reported_time:.3f}s exceeds 1.0s requirement"
            
            # Check output messages
            assert "Parsing BMAD files" in result.stdout
            assert "Found 1 agents" in result.stdout
            assert "Loading configuration" in result.stdout
            assert "Generating PocketFlow code" in result.stdout
            assert "Generation complete" in result.stdout
            
            # Verify generated files exist
            assert output_path.exists()
            
            # Check for expected files
            expected_files = [
                "app.py",
                "agents/__init__.py",
                "agents/test_agent.py",
                "utils.py"
            ]
            
            for expected_file in expected_files:
                file_path = output_path / expected_file
                assert file_path.exists(), f"Expected file not found: {expected_file}"
                
                # Verify file has content
                content = file_path.read_text()
                assert len(content.strip()) > 0, f"File is empty: {expected_file}"

    def test_cli_verbose_mode(self):
        """Test CLI with verbose flag provides detailed output."""
        project_root = Path(__file__).parent.parent.parent
        fixtures_path = project_root / "tests" / "fixtures" / "sample_agents"
        
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "generated"
            
            result = subprocess.run([
                "python", "scripts/bmad2pf.py",
                "--src", str(fixtures_path),
                "--out", str(output_path),
                "--verbose"
            ], capture_output=True, text=True, cwd=project_root)
            
            assert result.returncode == 0
            
            # Check verbose output appears in stderr
            assert "test_agent" in result.stderr  # Agent ID should be listed
            assert "Timing breakdown:" in result.stderr
            assert "Parsing:" in result.stderr
            assert "Config:" in result.stderr
            assert "Generation:" in result.stderr

    def test_generated_code_validity(self):
        """Test that generated Python code is syntactically valid."""
        project_root = Path(__file__).parent.parent.parent
        fixtures_path = project_root / "tests" / "fixtures" / "sample_agents"
        
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "generated"
            
            result = subprocess.run([
                "python", "scripts/bmad2pf.py",
                "--src", str(fixtures_path),
                "--out", str(output_path)
            ], capture_output=True, text=True, cwd=project_root)
            
            assert result.returncode == 0
            
            # Check all generated Python files for valid syntax
            python_files = list(output_path.glob("**/*.py"))
            assert len(python_files) > 0, "No Python files were generated"
            
            for py_file in python_files:
                content = py_file.read_text()
                
                try:
                    # Parse the file to check syntax
                    ast.parse(content)
                except SyntaxError as e:
                    pytest.fail(f"Generated file has syntax error: {py_file}\nError: {e}")

    def test_cli_exit_codes(self):
        """Test that CLI returns proper exit codes for different scenarios."""
        project_root = Path(__file__).parent.parent.parent
        
        # Test success case (exit code 0)
        fixtures_path = project_root / "tests" / "fixtures" / "sample_agents"
        with tempfile.TemporaryDirectory() as temp_dir:
            result = subprocess.run([
                "python", "scripts/bmad2pf.py",
                "--src", str(fixtures_path),
                "--out", str(temp_dir)
            ], capture_output=True, text=True, cwd=project_root)
            
            assert result.returncode == 0
        
        # Test file not found (exit code 5)
        result = subprocess.run([
            "python", "scripts/bmad2pf.py",
            "--src", "/non/existent/path"
        ], capture_output=True, text=True, cwd=project_root)
        
        assert result.returncode == 5

    def test_performance_requirement(self):
        """Test that generation completes within the 1-second requirement."""
        project_root = Path(__file__).parent.parent.parent
        fixtures_path = project_root / "tests" / "fixtures" / "sample_agents"
        
        # Run multiple times to ensure consistent performance
        execution_times = []
        
        for _ in range(3):
            with tempfile.TemporaryDirectory() as temp_dir:
                start_time = time.perf_counter()
                
                result = subprocess.run([
                    "python", "scripts/bmad2pf.py",
                    "--src", str(fixtures_path),
                    "--out", str(temp_dir)
                ], capture_output=True, text=True, cwd=project_root)
                
                end_time = time.perf_counter()
                execution_time = end_time - start_time
                execution_times.append(execution_time)
                
                assert result.returncode == 0
        
        # Check that all runs completed within 2 seconds (including subprocess overhead)
        max_time = max(execution_times)
        avg_time = sum(execution_times) / len(execution_times)
        
        assert max_time < 2.0, f"Maximum execution time {max_time:.3f}s exceeds 2.0s with subprocess overhead"
        
        # Print timing info for debugging
        print(f"Performance results: avg={avg_time:.3f}s, max={max_time:.3f}s")

    def test_cli_with_existing_bmad_files(self):
        """Test CLI with the actual BMAD files in the repository."""
        project_root = Path(__file__).parent.parent.parent
        bmad_path = project_root / "preprocessing"
        
        # Skip if no bmad directory exists
        if not bmad_path.exists():
            pytest.skip("No bmad directory found in project")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "generated"
            
            result = subprocess.run([
                "python", "scripts/bmad2pf.py",
                "--src", str(bmad_path),
                "--out", str(output_path)
            ], capture_output=True, text=True, cwd=project_root)
            
            # Should succeed even if no workflow.yaml exists
            # (config_loader should handle missing workflow gracefully)
            assert result.returncode in [0, 4], f"Unexpected exit code: {result.returncode}"
            
            if result.returncode == 0:
                # If successful, verify structure
                assert output_path.exists()
                python_files = list(output_path.glob("**/*.py"))
                assert len(python_files) > 0, "No Python files were generated"