#!/usr/bin/env python3
"""Integration tests for Docker build and deployment."""

import subprocess
import time
import pytest
from pathlib import Path


class TestDockerBuild:
    """Test Docker build process and image properties."""

    @pytest.fixture
    def project_root(self):
        """Get project root directory."""
        return Path(__file__).parent.parent.parent

    @pytest.fixture
    def dockerfile_path(self, project_root):
        """Get Dockerfile path."""
        return project_root / "Dockerfile"

    @pytest.fixture
    def dockerignore_path(self, project_root):
        """Get .dockerignore path."""
        return project_root / ".dockerignore"

    def test_dockerfile_exists(self, dockerfile_path):
        """Test that Dockerfile exists."""
        assert dockerfile_path.exists(), "Dockerfile should exist in project root"

    def test_dockerignore_exists(self, dockerignore_path):
        """Test that .dockerignore exists."""
        assert dockerignore_path.exists(), ".dockerignore should exist in project root"

    def test_dockerfile_has_multi_stage_structure(self, dockerfile_path):
        """Test that Dockerfile has proper multi-stage structure."""
        content = dockerfile_path.read_text()
        
        # Check for builder stage
        assert "FROM python:3.10-alpine AS builder" in content
        
        # Check for runtime stage
        assert "FROM python:3.10-alpine AS runtime" in content
        
        # Check for proper layer ordering
        assert content.index("AS builder") < content.index("AS runtime")

    def test_dockerfile_has_required_commands(self, dockerfile_path):
        """Test that Dockerfile includes all required commands."""
        content = dockerfile_path.read_text()
        
        # Check for generation command
        assert "bmad2pf.py" in content
        
        # Check for health check
        assert "HEALTHCHECK" in content
        
        # Check for proper CMD
        assert "uvicorn generated.app:app" in content
        
        # Check for build dependency cleanup
        assert "apk del .build-deps" in content

    def test_dockerfile_environment_variables(self, dockerfile_path):
        """Test that Dockerfile sets proper environment variables."""
        content = dockerfile_path.read_text()
        
        required_env_vars = [
            "PYTHONUNBUFFERED=1",
            "PORT=8000",
            "WORKERS=1",
            "LOG_LEVEL=info"
        ]
        
        for env_var in required_env_vars:
            assert env_var in content, f"Environment variable {env_var} should be set"

    def test_dockerignore_excludes_development_files(self, dockerignore_path):
        """Test that .dockerignore excludes development files."""
        content = dockerignore_path.read_text()
        
        excluded_patterns = [
            ".git/",
            "tests/",
            "__pycache__/",
            "*.pyc",
            ".env",
            "venv/",
            "generated/"  # Built inside container
        ]
        
        for pattern in excluded_patterns:
            assert pattern in content, f"Pattern {pattern} should be excluded"

    @pytest.mark.skipif(
        subprocess.run(["docker", "--version"], capture_output=True).returncode != 0,
        reason="Docker not available"
    )
    def test_multi_stage_build_succeeds(self, project_root):
        """Test that multi-stage Docker build completes successfully."""
        start_time = time.time()
        
        result = subprocess.run([
            "docker", "build", 
            "-t", "bmad-pocketflow-test",
            str(project_root)
        ], capture_output=True, text=True, timeout=120)
        
        build_time = time.time() - start_time
        
        assert result.returncode == 0, f"Build failed: {result.stderr}"
        assert build_time < 60, f"Build took {build_time:.1f}s, should be under 60s"

    @pytest.mark.skipif(
        subprocess.run(["docker", "--version"], capture_output=True).returncode != 0,
        reason="Docker not available"
    )  
    def test_generated_code_present_in_runtime(self):
        """Test that generated code is present in runtime image."""
        # Build and inspect image
        result = subprocess.run([
            "docker", "run", "--rm", "--entrypoint=ls",
            "bmad-pocketflow-test", "-la", "/app/generated"
        ], capture_output=True, text=True)
        
        assert result.returncode == 0, "Generated code directory should exist"
        assert "app.py" in result.stdout, "Generated app.py should be present"

    @pytest.mark.skipif(
        subprocess.run(["docker", "--version"], capture_output=True).returncode != 0,
        reason="Docker not available"
    )
    def test_bmad_sources_excluded_from_runtime(self):
        """Test that BMAD source files are excluded from runtime image."""
        result = subprocess.run([
            "docker", "run", "--rm", "--entrypoint=ls",
            "bmad-pocketflow-test", "/app/bmad"
        ], capture_output=True, text=True)
        
        # Should fail because bmad directory shouldn't exist in runtime
        assert result.returncode != 0, "BMAD sources should not be in runtime image"

    @pytest.mark.skipif(
        subprocess.run(["docker", "--version"], capture_output=True).returncode != 0,
        reason="Docker not available"
    )
    def test_health_check_endpoint_responds(self):
        """Test that health check endpoint is working.""" 
        # Start container in background
        container_result = subprocess.run([
            "docker", "run", "-d", "-p", "8000:8000",
            "--env", "OPENAI_API_KEY=test",
            "bmad-pocketflow-test"
        ], capture_output=True, text=True)
        
        if container_result.returncode != 0:
            pytest.skip("Could not start container")
        
        container_id = container_result.stdout.strip()
        
        try:
            # Wait for container to start
            time.sleep(5)
            
            # Test health endpoint
            health_result = subprocess.run([
                "curl", "-f", "http://localhost:8000/health"
            ], capture_output=True, text=True)
            
            assert health_result.returncode == 0, "Health endpoint should respond"
            
        finally:
            # Clean up container
            subprocess.run(["docker", "stop", container_id], capture_output=True)
            subprocess.run(["docker", "rm", container_id], capture_output=True)

    @pytest.mark.skipif(
        subprocess.run(["docker", "--version"], capture_output=True).returncode != 0,
        reason="Docker not available"
    )
    def test_image_size_under_200mb(self):
        """Test that final image size is under 200MB."""
        result = subprocess.run([
            "docker", "images", "bmad-pocketflow-test", 
            "--format", "{{.Size}}"
        ], capture_output=True, text=True)
        
        assert result.returncode == 0, "Could not get image size"
        
        size_str = result.stdout.strip()
        
        # Parse size (could be in MB or GB)
        if "GB" in size_str:
            pytest.fail(f"Image size {size_str} exceeds 200MB limit")
        elif "MB" in size_str:
            size_mb = float(size_str.replace("MB", ""))
            assert size_mb < 200, f"Image size {size_mb}MB exceeds 200MB limit"