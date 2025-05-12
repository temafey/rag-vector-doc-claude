"""
Tests for VectorRepository.
"""
import pytest
import time
from unittest.mock import patch, MagicMock
from typing import List, Dict, Any, Optional

from app.infrastructure.repositories.vector_repository import (
    VectorRepository, SearchResult, VectorCache, QdrantClientPool
)

class TestVectorCache:
    """Test cases for VectorCache."""
    
    def test_cache_get_set(self):
        """Test basic cache operations."""
        cache = VectorCache(max_size=10, ttl=3600)
        
        # Test parameters
        collection = "test_collection"
        query_vector = [0.1, 0.2, 0.3]
        limit = 5
        filter_condition = {"field": "value"}
        
        # Create sample results
        results = [
            SearchResult(id="1", score=0.9, metadata={"content": "Content 1"}),
            SearchResult(id="2", score=0.8, metadata={"content": "Content 2"})
        ]
        
        # Set in cache
        cache.set(collection, query_vector, limit, filter_condition, results)
        
        # Get from cache
        cached_results = cache.get(collection, query_vector, limit, filter_condition)
        
        # Verify we got the same results
        assert cached_results is not None
        assert len(cached_results) == len(results)
        assert cached_results[0].id == results[0].id
        assert cached_results[1].id == results[1].id
        
        # Check cache stats
        stats = cache.get_stats()
        assert stats["hits"] == 1
        assert stats["misses"] == 0
        
        # Try with different parameters
        different_results = cache.get(collection, [0.4, 0.5, 0.6], limit, filter_condition)
        assert different_results is None
        
        # Check cache stats again
        stats = cache.get_stats()
        assert stats["hits"] == 1
        assert stats["misses"] == 1
    
    def test_cache_ttl(self):
        """Test cache time-to-live expiration."""
        # Create cache with short TTL
        cache = VectorCache(max_size=10, ttl=0.1)  # 100ms TTL
        
        # Test parameters
        collection = "test_collection"
        query_vector = [0.1, 0.2, 0.3]
        limit = 5
        filter_condition = None
        
        # Create sample results
        results = [
            SearchResult(id="1", score=0.9, metadata={"content": "Content 1"})
        ]
        
        # Set in cache
        cache.set(collection, query_vector, limit, filter_condition, results)
        
        # Get from cache immediately (should be a hit)
        cached_results = cache.get(collection, query_vector, limit, filter_condition)
        assert cached_results is not None
        
        # Wait for TTL to expire
        time.sleep(0.2)
        
        # Get again (should be a miss)
        cached_results = cache.get(collection, query_vector, limit, filter_condition)
        assert cached_results is None
    
    def test_cache_max_size(self):
        """Test cache max size limits."""
        # Create cache with small size limit
        cache = VectorCache(max_size=3, ttl=3600)
        
        # Add multiple entries
        for i in range(5):
            collection = "test_collection"
            query_vector = [float(i), 0.0, 0.0]
            limit = 5
            filter_condition = None
            
            results = [
                SearchResult(id=str(i), score=0.9, metadata={"content": f"Content {i}"})
            ]
            
            cache.set(collection, query_vector, limit, filter_condition, results)
        
        # Check size is limited
        assert len(cache.cache) <= 3
        
        # Check at least the last entry is still there
        cached_results = cache.get("test_collection", [4.0, 0.0, 0.0], 5, None)
        assert cached_results is not None
        assert cached_results[0].id == "4"

class TestVectorRepository:
    """Test cases for VectorRepository with mocks."""
    
    @pytest.fixture
    def mock_qdrant_client(self):
        """Create a mock Qdrant client."""
        with patch("app.infrastructure.repositories.vector_repository.QdrantClient") as mock:
            # Setup mock collection list
            collections_mock = MagicMock()
            collections_mock.collections = [
                MagicMock(name="test_collection")
            ]
            mock.return_value.get_collections.return_value = collections_mock
            
            # Setup mock search results
            search_result1 = MagicMock(
                id="1", 
                score=0.9, 
                payload={"content": "Content 1"}
            )
            search_result2 = MagicMock(
                id="2", 
                score=0.8, 
                payload={"content": "Content 2"}
            )
            mock.return_value.search.return_value = [search_result1, search_result2]
            
            yield mock
    
    def test_vector_repository_search_with_cache(self, mock_qdrant_client):
        """Test search with caching."""
        # Create repository with mock
        repo = VectorRepository(host="localhost", port=6333, cache_size=10)
        
        # First search should use client
        results = repo.search(
            collection="test_collection",
            query_vector=[0.1, 0.2, 0.3],
            limit=5
        )
        
        # Check results
        assert len(results) == 2
        assert results[0].id == "1"
        assert results[1].id == "2"
        
        # Verify client was called once
        mock_qdrant_client.return_value.search.assert_called_once()
        
        # Reset mock
        mock_qdrant_client.return_value.search.reset_mock()
        
        # Second search with same parameters should use cache
        results = repo.search(
            collection="test_collection",
            query_vector=[0.1, 0.2, 0.3],
            limit=5
        )
        
        # Check results are still correct
        assert len(results) == 2
        assert results[0].id == "1"
        assert results[1].id == "2"
        
        # Verify client was NOT called again
        mock_qdrant_client.return_value.search.assert_not_called()
        
        # Search with different parameters should call client again
        repo.search(
            collection="test_collection",
            query_vector=[0.4, 0.5, 0.6],
            limit=5
        )
        
        # Verify client was called again
        mock_qdrant_client.return_value.search.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_async_search(self, mock_qdrant_client):
        """Test asynchronous search."""
        # Create repository with mock
        repo = VectorRepository(host="localhost", port=6333, cache_size=10)
        
        # Async search
        results = await repo.search_async(
            collection="test_collection",
            query_vector=[0.1, 0.2, 0.3],
            limit=5
        )
        
        # Check results
        assert len(results) == 2
        assert results[0].id == "1"
        assert results[1].id == "2"
        
        # Verify client was called
        mock_qdrant_client.return_value.search.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_batch_search(self, mock_qdrant_client):
        """Test batch search."""
        # Create repository with mock
        repo = VectorRepository(host="localhost", port=6333, cache_size=10)
        
        # Batch search
        query_vectors = [
            [0.1, 0.2, 0.3],
            [0.4, 0.5, 0.6]
        ]
        
        results = await repo.batch_search(
            collection="test_collection",
            query_vectors=query_vectors,
            limit=5
        )
        
        # Check results
        assert len(results) == 2  # Two queries
        assert len(results[0]) == 2  # Two results per query
        assert len(results[1]) == 2
        
        # Verify client was called for each query
        assert mock_qdrant_client.return_value.search.call_count == 2
