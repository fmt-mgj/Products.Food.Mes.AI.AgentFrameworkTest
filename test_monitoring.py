"""Simple test to verify monitoring implementation works."""

import json
import os
import tempfile
from pathlib import Path

# Test logging configuration
def test_logging_config():
    """Test that logging configuration works correctly."""
    try:
        from generated.logging_config import setup_logging, JSONFormatter, sanitize_sensitive_data
        
        # Test JSON formatter
        formatter = JSONFormatter()
        assert formatter is not None
        
        # Test logger setup
        logger = setup_logging(log_level="INFO", json_format=False)
        assert logger is not None
        
        # Test sensitive data sanitization
        sensitive_data = {
            "user": "test",
            "password": "secret123",
            "api_key": "sk-abcd1234",
            "nested": {
                "secret": "hidden",
                "normal": "visible"
            }
        }
        
        sanitized = sanitize_sensitive_data(sensitive_data)
        assert sanitized["user"] == "test"
        assert sanitized["password"] == "***REDACTED***"
        assert sanitized["api_key"] == "***REDACTED***"
        assert sanitized["nested"]["secret"] == "***REDACTED***"
        assert sanitized["nested"]["normal"] == "visible"
        
        print("OK: Logging configuration test passed")
        return True
    except Exception as e:
        print(f"FAIL: Logging configuration test failed: {e}")
        return False


def test_memory_metrics():
    """Test that memory metrics are collected properly."""
    try:
        from generated.memory import MemoryManager
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create memory manager
            memory_manager = MemoryManager(memory_dir=temp_dir)
            
            # Test initial stats
            stats = memory_manager.get_cache_stats()
            assert "cache_size" in stats
            assert "operation_count" in stats
            assert "cache_hit_rate" in stats
            assert "memory_size_kb" in stats
            
            # Test health check
            health = memory_manager.health_check()
            assert health in ["healthy", "warning", "error"]
            
            print("OK: Memory metrics test passed")
            return True
    except Exception as e:
        print(f"FAIL: Memory metrics test failed: {e}")
        return False


def test_health_endpoint():
    """Test that health endpoint returns correct structure."""
    try:
        from generated.app import HealthResponse
        
        # Test response model
        health_response = HealthResponse(
            status="healthy",
            version="test",
            agents_loaded=2,
            timestamp="2025-01-15T10:30:45.123Z",
            uptime_seconds=120.5,
            startup_time=0.8,
            metrics={
                "memory_mb": 45.2,
                "cpu_percent": 12.3,
                "threads": 8
            },
            dependencies={
                "pocketflow": "healthy",
                "memory_backend": "healthy"
            }
        )
        
        # Validate structure
        assert health_response.status == "healthy"
        assert health_response.version == "test"
        assert health_response.agents_loaded == 2
        assert isinstance(health_response.metrics, dict)
        assert isinstance(health_response.dependencies, dict)
        
        print("OK: Health endpoint test passed")
        return True
    except Exception as e:
        print(f"FAIL: Health endpoint test failed: {e}")
        return False


def test_opentelemetry_optional():
    """Test that OpenTelemetry integration is optional."""
    try:
        from generated.executor import OTEL_AVAILABLE, otel_tracer
        
        # Should not fail even if OTel is not installed
        assert isinstance(OTEL_AVAILABLE, bool)
        
        if OTEL_AVAILABLE:
            assert otel_tracer is not None
            print("OK: OpenTelemetry is available and configured")
        else:
            assert otel_tracer is None
            print("OK: OpenTelemetry is not available (optional)")
        
        print("OK: OpenTelemetry optional test passed")
        return True
    except Exception as e:
        print(f"FAIL: OpenTelemetry optional test failed: {e}")
        return False


def test_middleware_import():
    """Test that middleware can be imported and used."""
    try:
        from generated.middleware import logging_middleware, get_request_id_from_request
        
        # Should be able to import without errors
        assert logging_middleware is not None
        assert get_request_id_from_request is not None
        
        print("OK: Middleware import test passed")
        return True
    except Exception as e:
        print(f"FAIL: Middleware import test failed: {e}")
        return False


def run_all_tests():
    """Run all monitoring tests."""
    print("Running monitoring implementation tests...")
    print("-" * 50)
    
    tests = [
        test_logging_config,
        test_memory_metrics,
        test_health_endpoint,
        test_opentelemetry_optional,
        test_middleware_import,
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()
    
    print("-" * 50)
    print(f"Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("SUCCESS: All monitoring tests passed!")
        return True
    else:
        print(f"FAILED: {total - passed} tests failed")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)