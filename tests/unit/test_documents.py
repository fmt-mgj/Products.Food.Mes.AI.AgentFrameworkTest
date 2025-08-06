# Unit tests for Document Storage API - Story 2.2
# Tests all CRUD operations, security validation, error handling, and async operations

import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock

from httpx import AsyncClient
from fastapi import FastAPI

from generated.documents import router, DocumentId, DocumentContent, DOCS_DIR


@pytest.fixture
def app():
    """Create FastAPI app with documents router for testing"""
    test_app = FastAPI()
    test_app.include_router(router)
    return test_app


@pytest.fixture
def client(app):
    """Create test client"""
    import httpx
    return httpx.Client(transport=httpx.ASGITransport(app=app), base_url="http://test")


@pytest.fixture
def temp_docs_dir():
    """Create temporary docs directory for testing"""
    temp_dir = tempfile.mkdtemp()
    temp_path = Path(temp_dir)
    
    # Patch DOCS_DIR globally for all tests
    with patch('generated.documents.DOCS_DIR', temp_path):
        yield temp_path
    
    # Cleanup
    shutil.rmtree(temp_dir)


class TestDocumentValidation:
    """Test document ID and content validation"""
    
    def test_valid_document_ids(self):
        """Test that valid document IDs are accepted"""
        valid_ids = ["test", "test-doc", "test_doc", "abc123", "a-b_c-1-2-3"]
        
        for valid_id in valid_ids:
            doc_id = DocumentId(id=valid_id)
            assert doc_id.id == valid_id
    
    def test_invalid_document_ids(self):
        """Test that invalid document IDs are rejected"""
        dangerous_ids = [
            "../etc/passwd",      # Path traversal
            "../../secret",       # Path traversal  
            "path/to/file",       # Forward slash
            "file\\path",         # Backslash
            "doc.txt",            # Dot (could be used for traversal)
            "doc with spaces",    # Spaces
            "doc@email.com",      # Special characters
            "",                   # Empty string
            "a" * 101,           # Too long
        ]
        
        for bad_id in dangerous_ids:
            with pytest.raises(ValueError):
                DocumentId(id=bad_id)
    
    def test_valid_document_content(self):
        """Test that valid document content is accepted"""
        valid_content = [
            "# Test Document",
            "Short content",
            "# Long Document\n" + "Line\n" * 1000,  # Under 100KB limit
            "",  # Empty content is valid
        ]
        
        for content in valid_content:
            doc_content = DocumentContent(content=content)
            assert doc_content.content == content
    
    def test_invalid_document_content(self):
        """Test that oversized content is rejected"""
        # Content over 100KB should be rejected
        large_content = "x" * 100_001
        
        with pytest.raises(ValueError, match="Document too large"):
            DocumentContent(content=large_content)


class TestDocumentEndpoints:
    """Test document storage API endpoints"""
    
    def test_get_document_success(self, client, temp_docs_dir):
        """Test successful document retrieval"""
        # Create test document
        test_content = "# Test Document\n\nThis is a test."
        test_file = temp_docs_dir / "test-doc.md"
        test_file.write_text(test_content, encoding='utf-8')
        
        # Test endpoint
        response = client.get("/doc/test-doc")
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/markdown; charset=utf-8"
        assert response.text == test_content
    
    def test_get_document_not_found(self, client, temp_docs_dir):
        """Test 404 for missing documents"""
        response = client.get("/doc/nonexistent")
        
        assert response.status_code == 404
        assert response.json()["detail"] == "Document not found"
    
    def test_get_document_invalid_id(self, client):
        """Test 400 for invalid document IDs"""
        response = client.get("/doc/../secret")
        
        assert response.status_code == 400
        assert "Invalid document ID format" in response.json()["detail"]
    
    def test_put_document_success(self, client, temp_docs_dir):
        """Test successful document creation"""
        test_content = "# New Document\n\nThis is new content."
        
        response = client.put(
            "/doc/new-doc",
            json={"content": test_content}
        )
        
        assert response.status_code == 200
        assert response.json()["message"] == "Document saved"
        assert response.json()["id"] == "new-doc"
        
        # Verify file was created
        test_file = temp_docs_dir / "new-doc.md"
        assert test_file.exists()
        assert test_file.read_text(encoding='utf-8') == test_content
    
    def test_put_document_update(self, client, temp_docs_dir):
        """Test successful document update"""
        # Create initial document
        initial_content = "# Initial Content"
        test_file = temp_docs_dir / "update-doc.md"
        test_file.write_text(initial_content, encoding='utf-8')
        
        # Update document
        new_content = "# Updated Content\n\nThis has been updated."
        response = client.put(
            "/doc/update-doc",
            json={"content": new_content}
        )
        
        assert response.status_code == 200
        assert response.json()["message"] == "Document saved"
        
        # Verify content was updated
        assert test_file.read_text(encoding='utf-8') == new_content
    
    def test_put_document_invalid_id(self, client):
        """Test 400 for invalid document ID in PUT"""
        response = client.put(
            "/doc/../../secret",
            json={"content": "malicious content"}
        )
        
        assert response.status_code == 400
        assert "Invalid document ID format" in response.json()["detail"]
    
    def test_put_document_invalid_content(self, client):
        """Test 422 for invalid content validation"""
        large_content = "x" * 100_001
        
        response = client.put(
            "/doc/test-doc",
            json={"content": large_content}
        )
        
        assert response.status_code == 422  # Pydantic validation error
    
    def test_get_status_existing_document(self, client, temp_docs_dir):
        """Test status endpoint for existing document"""
        # Create test document
        test_file = temp_docs_dir / "existing-doc.md"
        test_file.write_text("Test content", encoding='utf-8')
        
        response = client.get("/doc/existing-doc/status")
        
        assert response.status_code == 200
        assert response.json()["exists"] is True
    
    def test_get_status_missing_document(self, client, temp_docs_dir):
        """Test status endpoint for missing document"""
        response = client.get("/doc/missing-doc/status")
        
        assert response.status_code == 200
        assert response.json()["exists"] is False
    
    def test_get_status_invalid_id(self, client):
        """Test 400 for invalid document ID in status check"""
        response = client.get("/doc/../etc/passwd/status")
        
        assert response.status_code == 400
        assert "Invalid document ID format" in response.json()["detail"]


class TestAsyncFileOperations:
    """Test async file operations and error handling"""
    
    @pytest.mark.asyncio
    async def test_async_get_document(self, app, temp_docs_dir):
        """Test async document retrieval"""
        # Create test document
        test_content = "# Async Test\n\nTesting async operations."
        test_file = temp_docs_dir / "async-test.md"
        test_file.write_text(test_content, encoding='utf-8')
        
        import httpx
        with httpx.Client(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            response = client.get("/doc/async-test")
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/markdown; charset=utf-8"
        assert response.text == test_content
    
    @pytest.mark.asyncio
    async def test_async_put_document(self, app, temp_docs_dir):
        """Test async document creation"""
        test_content = "# Async Put Test\n\nTesting async put operations."
        
        import httpx
        with httpx.Client(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            response = client.put(
                "/doc/async-put-test",
                json={"content": test_content}
            )
        
        assert response.status_code == 200
        assert response.json()["message"] == "Document saved"
        
        # Verify file was created
        test_file = temp_docs_dir / "async-put-test.md"
        assert test_file.exists()
        assert test_file.read_text(encoding='utf-8') == test_content
    
    def test_file_read_error_handling(self, client, temp_docs_dir):
        """Test graceful handling of file read errors"""
        # Create a file and then make it unreadable by patching aiofiles
        test_file = temp_docs_dir / "error-test.md"
        test_file.write_text("Test content", encoding='utf-8')
        
        with patch('aiofiles.open', side_effect=Exception("File read error")):
            response = client.get("/doc/error-test")
            
            assert response.status_code == 500
            assert "Failed to read document" in response.json()["detail"]
    
    def test_file_write_error_handling(self, client, temp_docs_dir):
        """Test graceful handling of file write errors"""
        with patch('aiofiles.open', side_effect=Exception("File write error")):
            response = client.put(
                "/doc/error-test",
                json={"content": "Test content"}
            )
            
            assert response.status_code == 500
            assert "Failed to write document" in response.json()["detail"]


class TestSecurityValidation:
    """Test security validation and path traversal prevention"""
    
    def test_path_traversal_prevention_get(self, client):
        """Test that path traversal attacks are blocked in GET requests"""
        dangerous_paths = [
            "../config",
            "../../secrets",
            "..\\windows\\system32",
            "./../../../etc/passwd",
            "....//....//etc//passwd",
        ]
        
        for dangerous_path in dangerous_paths:
            response = client.get(f"/doc/{dangerous_path}")
            assert response.status_code == 400
            assert "Invalid document ID format" in response.json()["detail"]
    
    def test_path_traversal_prevention_put(self, client):
        """Test that path traversal attacks are blocked in PUT requests"""
        dangerous_paths = [
            "../config",
            "../../secrets", 
            "..\\windows\\system32",
            "./../../../etc/passwd",
        ]
        
        for dangerous_path in dangerous_paths:
            response = client.put(
                f"/doc/{dangerous_path}",
                json={"content": "malicious content"}
            )
            assert response.status_code == 400
            assert "Invalid document ID format" in response.json()["detail"]
    
    def test_path_traversal_prevention_status(self, client):
        """Test that path traversal attacks are blocked in status requests"""
        dangerous_paths = [
            "../config", 
            "../../secrets",
            "..\\windows\\system32",
        ]
        
        for dangerous_path in dangerous_paths:
            response = client.get(f"/doc/{dangerous_path}/status")
            assert response.status_code == 400
            assert "Invalid document ID format" in response.json()["detail"]
    
    def test_directory_creation_security(self, client):
        """Test that docs directory is created safely"""
        with patch('pathlib.Path.mkdir', side_effect=Exception("Permission denied")):
            response = client.put(
                "/doc/test-doc",
                json={"content": "test content"}
            )
            
            assert response.status_code == 500
            assert "Failed to create docs directory" in response.json()["detail"]


class TestContentTypeHeaders:
    """Test proper Content-Type headers"""
    
    def test_markdown_content_type(self, client, temp_docs_dir):
        """Test that GET returns proper Content-Type header"""
        # Create test document
        test_file = temp_docs_dir / "content-type-test.md"
        test_file.write_text("# Content Type Test", encoding='utf-8')
        
        response = client.get("/doc/content-type-test")
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/markdown; charset=utf-8"
    
    def test_json_response_content_type(self, client, temp_docs_dir):
        """Test that PUT and status endpoints return JSON"""
        # Test PUT response
        response = client.put(
            "/doc/json-test",
            json={"content": "# JSON Test"}
        )
        
        assert response.status_code == 200
        assert "application/json" in response.headers["content-type"]
        
        # Test status response
        response = client.get("/doc/json-test/status")
        
        assert response.status_code == 200
        assert "application/json" in response.headers["content-type"]


# Performance and edge case tests
class TestEdgeCases:
    """Test edge cases and performance scenarios"""
    
    def test_empty_document_content(self, client, temp_docs_dir):
        """Test handling of empty documents"""
        # Create empty document
        response = client.put(
            "/doc/empty-doc",
            json={"content": ""}
        )
        
        assert response.status_code == 200
        
        # Retrieve empty document
        response = client.get("/doc/empty-doc")
        
        assert response.status_code == 200
        assert response.text == ""
    
    def test_unicode_content(self, client, temp_docs_dir):
        """Test handling of Unicode content"""
        unicode_content = "# Unicode Test\n\n🚀 Emoji test\nÄÖÜäöü German\n中文 Chinese"
        
        # Store Unicode content
        response = client.put(
            "/doc/unicode-test",
            json={"content": unicode_content}
        )
        
        assert response.status_code == 200
        
        # Retrieve Unicode content
        response = client.get("/doc/unicode-test")
        
        assert response.status_code == 200
        assert response.text == unicode_content
    
    def test_large_valid_document(self, client, temp_docs_dir):
        """Test handling of large but valid documents"""
        # Create content just under the limit (100KB)
        large_content = "# Large Document\n" + "Line of content\n" * 5000  # ~90KB
        
        response = client.put(
            "/doc/large-doc",
            json={"content": large_content}
        )
        
        assert response.status_code == 200
        
        # Retrieve large document
        response = client.get("/doc/large-doc")
        
        assert response.status_code == 200
        assert response.text == large_content
    
    def test_concurrent_access_simulation(self, client, temp_docs_dir):
        """Test that concurrent access doesn't cause issues"""
        # This is a basic test - in production you'd use proper async testing
        content1 = "# Document Version 1"
        content2 = "# Document Version 2"
        
        # Simulate concurrent writes (synchronous for testing)
        response1 = client.put("/doc/concurrent-test", json={"content": content1})
        response2 = client.put("/doc/concurrent-test", json={"content": content2})
        
        assert response1.status_code == 200
        assert response2.status_code == 200
        
        # The last write should win
        response = client.get("/doc/concurrent-test")
        assert response.status_code == 200
        assert response.text == content2