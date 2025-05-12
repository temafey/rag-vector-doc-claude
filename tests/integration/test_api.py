"""
Integration tests for API endpoints.
"""
import pytest
import json
import os
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from app.main import create_app
from app.infrastructure.command_bus import command_bus
from app.infrastructure.query_bus import query_bus
from app.application.commands.document_commands import AddDocumentCommand, AddDocumentResult
from app.application.queries.document_queries import (
    SearchQuery, SearchResult, SearchSource,
    ListCollectionsQuery, ListCollectionsResult, CollectionInfo
)

@pytest.fixture
def api_client():
    """Create a FastAPI TestClient."""
    app = create_app()
    return TestClient(app)

@pytest.fixture
def mock_command_bus():
    """Mock command bus for tests."""
    with patch('app.api.routes.command_bus') as mock:
        # Setup mocks for common commands
        mock.dispatch.side_effect = lambda cmd: _mock_command_dispatch(cmd)
        yield mock

@pytest.fixture
def mock_query_bus():
    """Mock query bus for tests."""
    with patch('app.api.routes.query_bus') as mock:
        # Setup mocks for common queries
        mock.dispatch.side_effect = lambda query: _mock_query_dispatch(query)
        yield mock

def _mock_command_dispatch(command):
    """Mock implementation of command_bus.dispatch."""
    if isinstance(command, AddDocumentCommand):
        return AddDocumentResult(
            document_id=command.id,
            chunk_count=3
        )
    return None

def _mock_query_dispatch(query):
    """Mock implementation of query_bus.dispatch."""
    if isinstance(query, SearchQuery):
        return SearchResult(
            response="Generated response based on search query",
            sources=[
                SearchSource(
                    id="chunk1",
                    title="Test Document",
                    content="Test content",
                    metadata={"language": "en"},
                    score=0.95
                )
            ],
            query_language="en",
            response_language="en"
        )
    elif isinstance(query, ListCollectionsQuery):
        return ListCollectionsResult(
            collections=[
                CollectionInfo(
                    name="test",
                    document_count=10,
                    vector_dimension=1536
                ),
                CollectionInfo(
                    name="default",
                    document_count=5,
                    vector_dimension=1536
                )
            ]
        )
    return None

class TestAPI:
    """Test cases for API endpoints."""
    
    def test_health_endpoint(self, api_client):
        """Test health check endpoint."""
        response = api_client.get("/health")
        
        assert response.status_code == 200
        assert "status" in response.json()
        assert response.json()["status"] == "ok"
    
    def test_search_endpoint(self, api_client, mock_query_bus):
        """Test search endpoint."""
        # Prepare request data
        request_data = {
            "query": "Test search query",
            "collection": "test",
            "limit": 5
        }
        
        # Make request
        response = api_client.post("/search", json=request_data)
        
        # Check response
        assert response.status_code == 200
        assert "response" in response.json()
        assert "sources" in response.json()
        assert "query_language" in response.json()
        assert "response_language" in response.json()
        
        # Verify query bus was called
        mock_query_bus.dispatch.assert_called_once()
        
        # Verify correct query object was created
        args, kwargs = mock_query_bus.dispatch.call_args
        assert isinstance(args[0], SearchQuery)
        assert args[0].query_text == request_data["query"]
        assert args[0].collection == request_data["collection"]
        assert args[0].limit == request_data["limit"]
    
    def test_add_document_endpoint(self, api_client, mock_command_bus):
        """Test add document endpoint."""
        # Prepare request data
        request_data = {
            "content": "Test document content",
            "metadata": {"title": "Test Document"},
            "collection": "test"
        }
        
        # Make request
        response = api_client.post("/documents", json=request_data)
        
        # Check response
        assert response.status_code == 200
        assert "id" in response.json()
        assert "metadata" in response.json()
        assert "chunk_count" in response.json()
        assert response.json()["chunk_count"] == 3
        
        # Verify command bus was called
        mock_command_bus.dispatch.assert_called_once()
        
        # Verify correct command object was created
        args, kwargs = mock_command_bus.dispatch.call_args
        assert isinstance(args[0], AddDocumentCommand)
        assert args[0].content == request_data["content"]
        assert args[0].metadata == request_data["metadata"]
        assert args[0].collection == request_data["collection"]
    
    def test_list_collections_endpoint(self, api_client, mock_query_bus):
        """Test list collections endpoint."""
        # Make request
        response = api_client.get("/collections")
        
        # Check response
        assert response.status_code == 200
        assert isinstance(response.json(), list)
        assert len(response.json()) == 2
        assert "name" in response.json()[0]
        assert "document_count" in response.json()[0]
        assert "vector_dimension" in response.json()[0]
        
        # Verify query bus was called
        mock_query_bus.dispatch.assert_called_once()
        
        # Verify correct query object was created
        args, kwargs = mock_query_bus.dispatch.call_args
        assert isinstance(args[0], ListCollectionsQuery)
    
    def test_create_collection_endpoint(self, api_client, mock_command_bus):
        """Test create collection endpoint."""
        # Make request
        response = api_client.post("/collections/new_collection")
        
        # Check response
        assert response.status_code == 200
        assert "message" in response.json()
        assert "new_collection" in response.json()["message"]
        
        # Verify command bus was called
        mock_command_bus.dispatch.assert_called_once()
    
    def test_async_upload_endpoint(self, api_client, mock_command_bus):
        """Test asynchronous document upload endpoint."""
        # Create a test file
        test_content = b"Test file content"
        
        # Make request
        response = api_client.post(
            "/documents/upload/async",
            files={"file": ("test.txt", test_content)},
            data={"collection": "test", "metadata": '{"title": "Test File"}'}
        )
        
        # Check response
        assert response.status_code == 200
        assert "task_id" in response.json()
        assert response.json()["status"] == "pending"
    
    def test_error_handling(self, api_client):
        """Test error handling in API."""
        # Test with invalid JSON
        response = api_client.post(
            "/documents",
            headers={"Content-Type": "application/json"},
            content="{invalid json"
        )
        
        # Check error response structure
        assert response.status_code >= 400
        assert "detail" in response.json()
    
    def test_validation(self, api_client):
        """Test request validation."""
        # Test with missing required field
        response = api_client.post(
            "/search",
            json={"collection": "test", "limit": 5}  # Missing 'query'
        )
        
        # Check validation error
        assert response.status_code == 422  # Unprocessable Entity
        assert "detail" in response.json()
