import os
import yaml
import toml
import pytest
from pathlib import Path


class TestDeploymentConfigurations:
    """Test deployment configuration files"""

    @pytest.fixture
    def deployment_dir(self):
        """Get deployment directory path"""
        return Path("deployment")

    def test_railway_toml_exists(self, deployment_dir):
        """Test that railway.toml exists"""
        railway_file = deployment_dir / "railway.toml"
        assert railway_file.exists(), "railway.toml should exist in deployment directory"

    def test_railway_toml_valid_syntax(self, deployment_dir):
        """Test that railway.toml has valid TOML syntax"""
        railway_file = deployment_dir / "railway.toml"
        with open(railway_file, 'r') as f:
            config = toml.load(f)
        
        # Verify required sections exist
        assert 'build' in config, "railway.toml should have [build] section"
        assert 'deploy' in config, "railway.toml should have [deploy] section"

    def test_railway_toml_configuration(self, deployment_dir):
        """Test railway.toml configuration values"""
        railway_file = deployment_dir / "railway.toml"
        with open(railway_file, 'r') as f:
            config = toml.load(f)
        
        # Check build configuration
        assert config['build']['builder'] == "DOCKERFILE"
        assert config['build']['dockerfilePath'] == "./Dockerfile"
        
        # Check deploy configuration
        assert config['deploy']['healthcheckPath'] == "/health"
        assert config['deploy']['healthcheckTimeout'] == 100
        assert config['deploy']['restartPolicyType'] == "ON_FAILURE"
        assert config['deploy']['restartPolicyMaxRetries'] == 3

    def test_fly_toml_exists(self, deployment_dir):
        """Test that fly.toml exists"""
        fly_file = deployment_dir / "fly.toml"
        assert fly_file.exists(), "fly.toml should exist in deployment directory"

    def test_fly_toml_valid_syntax(self, deployment_dir):
        """Test that fly.toml has valid TOML syntax"""
        fly_file = deployment_dir / "fly.toml"
        with open(fly_file, 'r') as f:
            config = toml.load(f)
        
        # Verify required fields exist
        assert 'app' in config, "fly.toml should have app name"
        assert 'primary_region' in config, "fly.toml should have primary_region"
        assert 'build' in config, "fly.toml should have [build] section"
        assert 'env' in config, "fly.toml should have [env] section"

    def test_fly_toml_configuration(self, deployment_dir):
        """Test fly.toml configuration values"""
        fly_file = deployment_dir / "fly.toml"
        with open(fly_file, 'r') as f:
            config = toml.load(f)
        
        # Check app configuration
        assert config['app'] == "bmad-pocketflow"
        assert config['primary_region'] == "iad"
        
        # Check build configuration
        assert config['build']['dockerfile'] == "Dockerfile"
        
        # Check environment variables
        assert config['env']['PORT'] == "8000"
        assert config['env']['MEMORY_BACKEND'] == "file"
        assert config['env']['LOG_LEVEL'] == "info"
        
        # Check services exist
        assert 'services' in config
        assert len(config['services']) > 0

    def test_fly_toml_health_check(self, deployment_dir):
        """Test fly.toml health check configuration"""
        fly_file = deployment_dir / "fly.toml"
        with open(fly_file, 'r') as f:
            config = toml.load(f)
        
        # Find health check in services
        service = config['services'][0]
        http_checks = service.get('http_checks', [])
        
        if http_checks:
            health_check = http_checks[0]
            assert health_check['path'] == "/health"
            assert health_check['method'] == "get"

    def test_cloud_run_yaml_exists(self, deployment_dir):
        """Test that cloud-run-service.yaml exists"""
        cloud_run_file = deployment_dir / "cloud-run-service.yaml"
        assert cloud_run_file.exists(), "cloud-run-service.yaml should exist in deployment directory"

    def test_cloud_run_yaml_valid_syntax(self, deployment_dir):
        """Test that cloud-run-service.yaml has valid YAML syntax"""
        cloud_run_file = deployment_dir / "cloud-run-service.yaml"
        with open(cloud_run_file, 'r') as f:
            config = yaml.safe_load(f)
        
        # Verify required Kubernetes fields
        assert config['apiVersion'] == "serving.knative.dev/v1"
        assert config['kind'] == "Service"
        assert 'metadata' in config
        assert 'spec' in config

    def test_cloud_run_yaml_configuration(self, deployment_dir):
        """Test cloud-run-service.yaml configuration values"""
        cloud_run_file = deployment_dir / "cloud-run-service.yaml"
        with open(cloud_run_file, 'r') as f:
            config = yaml.safe_load(f)
        
        # Check metadata
        assert config['metadata']['name'] == "bmad-pocketflow"
        
        # Check template spec
        template_spec = config['spec']['template']['spec']
        assert template_spec['containerConcurrency'] == 100
        assert template_spec['timeoutSeconds'] == 300
        
        # Check container configuration
        container = template_spec['containers'][0]
        assert any(port['containerPort'] == 8000 for port in container['ports'])
        
        # Check environment variables
        env_vars = {env['name']: env['value'] for env in container['env'] if 'value' in env}
        assert env_vars['PORT'] == "8000"
        assert env_vars['MEMORY_BACKEND'] == "file"
        assert env_vars['LOG_LEVEL'] == "info"

    def test_cloud_run_yaml_health_check(self, deployment_dir):
        """Test cloud-run-service.yaml health check configuration"""
        cloud_run_file = deployment_dir / "cloud-run-service.yaml"
        with open(cloud_run_file, 'r') as f:
            config = yaml.safe_load(f)
        
        container = config['spec']['template']['spec']['containers'][0]
        
        # Check liveness probe
        assert 'livenessProbe' in container
        liveness_probe = container['livenessProbe']
        assert liveness_probe['httpGet']['path'] == "/health"
        assert liveness_probe['httpGet']['port'] == 8000
        
        # Check readiness probe
        assert 'readinessProbe' in container
        readiness_probe = container['readinessProbe']
        assert readiness_probe['httpGet']['path'] == "/health"
        assert readiness_probe['httpGet']['port'] == 8000

    def test_cloud_run_yaml_autoscaling(self, deployment_dir):
        """Test cloud-run-service.yaml autoscaling configuration"""
        cloud_run_file = deployment_dir / "cloud-run-service.yaml"
        with open(cloud_run_file, 'r') as f:
            config = yaml.safe_load(f)
        
        annotations = config['spec']['template']['metadata']['annotations']
        assert annotations['autoscaling.knative.dev/minScale'] == "0"
        assert annotations['autoscaling.knative.dev/maxScale'] == "10"

    def test_cloud_run_yaml_resource_limits(self, deployment_dir):
        """Test cloud-run-service.yaml resource limits"""
        cloud_run_file = deployment_dir / "cloud-run-service.yaml"
        with open(cloud_run_file, 'r') as f:
            config = yaml.safe_load(f)
        
        container = config['spec']['template']['spec']['containers'][0]
        resources = container['resources']['limits']
        assert resources['cpu'] == "1"
        assert resources['memory'] == "512Mi"


class TestDeploymentDocumentation:
    """Test deployment documentation files"""

    def test_deployment_guide_exists(self):
        """Test that deployment guide exists"""
        guide_file = Path("docs/deployment-guide.md")
        assert guide_file.exists(), "deployment-guide.md should exist in docs directory"

    def test_monitoring_logging_guide_exists(self):
        """Test that monitoring guide exists"""
        monitoring_file = Path("docs/monitoring-logging.md")
        assert monitoring_file.exists(), "monitoring-logging.md should exist in docs directory"

    def test_deployment_guide_content(self):
        """Test deployment guide has required content"""
        guide_file = Path("docs/deployment-guide.md")
        with open(guide_file, 'r') as f:
            content = f.read()
        
        # Check for platform sections
        assert "Railway Deployment" in content
        assert "Fly.io Deployment" in content
        assert "Google Cloud Run Deployment" in content
        assert "Rollback Procedures" in content
        assert "Troubleshooting" in content

    def test_monitoring_guide_content(self):
        """Test monitoring guide has required content"""
        monitoring_file = Path("docs/monitoring-logging.md")
        with open(monitoring_file, 'r') as f:
            content = f.read()
        
        # Check for platform sections
        assert "Railway" in content
        assert "Fly.io" in content
        assert "Google Cloud Run" in content
        assert "Health Check Endpoint" in content