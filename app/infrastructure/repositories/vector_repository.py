"""
Repository for vector database operations with caching and improved performance.
"""
from typing import List, Dict, Any, Optional, Tuple, Union, Set
from dataclasses import dataclass
import time
import logging
import hashlib
import json
from functools import lru_cache
from threading import Lock
import concurrent.futures
import asyncio
from qdrant_client import QdrantClient
from qdrant_client.http import models
from qdrant_client.http.exceptions import UnexpectedResponse
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter
from qdrant_client.models import FieldCondition, MatchValue, Range, HasIdCondition

# Configure logging
logger = logging.getLogger(__name__)

@dataclass
class SearchResult:
    """Search result from vector database."""
    id: str
    score: float
    metadata: Dict[str, Any]

class VectorCache:
    """Cache for vector search results."""
    
    def __init__(self, max_size: int = 1000, ttl: int = 3600):
        """
        Initialize cache.
        
        Args:
            max_size: Maximum number of entries in cache
            ttl: Time to live in seconds
        """
        self.cache: Dict[str, Tuple[List[SearchResult], float]] = {}
        self.max_size = max_size
        self.ttl = ttl
        self.lock = Lock()
        self.hits = 0
        self.misses = 0
    
    def get_cache_key(self, collection: str, query_vector: List[float], 
                     limit: int, filter_condition: Optional[Dict[str, Any]]) -> str:
        """Generate a unique cache key for search parameters."""
        # Create a JSON-serializable representation of filter condition
        filter_str = json.dumps(filter_condition, sort_keys=True) if filter_condition else "null"
        
        # Use hash for query vector to avoid extremely long keys
        vector_hash = hashlib.md5(str(query_vector).encode('utf-8')).hexdigest()
        
        return f"{collection}:{vector_hash}:limit={limit}:filter={filter_str}"
    
    def get(self, collection: str, query_vector: List[float], 
           limit: int, filter_condition: Optional[Dict[str, Any]]) -> Optional[List[SearchResult]]:
        """Get cached search results if available and not expired."""
        key = self.get_cache_key(collection, query_vector, limit, filter_condition)
        
        with self.lock:
            if key in self.cache:
                results, timestamp = self.cache[key]
                
                # Check if cache entry is still valid
                if time.time() - timestamp <= self.ttl:
                    self.hits += 1
                    return results
                
                # Remove expired entry
                del self.cache[key]
        
        self.misses += 1
        return None
    
    def set(self, collection: str, query_vector: List[float], 
           limit: int, filter_condition: Optional[Dict[str, Any]], 
           results: List[SearchResult]) -> None:
        """Set search results in cache."""
        key = self.get_cache_key(collection, query_vector, limit, filter_condition)
        
        with self.lock:
            # Evict oldest entries if cache is full
            if len(self.cache) >= self.max_size:
                # Sort by timestamp and remove oldest 10%
                items = sorted(self.cache.items(), key=lambda item: item[1][1])
                for i in range(max(1, self.max_size // 10)):
                    if items:
                        old_key, _ = items[i]
                        del self.cache[old_key]
            
            # Add new entry
            self.cache[key] = (results, time.time())
    
    def clear(self) -> None:
        """Clear cache."""
        with self.lock:
            self.cache.clear()
            self.hits = 0
            self.misses = 0
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self.lock:
            return {
                "size": len(self.cache),
                "max_size": self.max_size,
                "ttl": self.ttl,
                "hits": self.hits,
                "misses": self.misses,
                "hit_ratio": self.hits / (self.hits + self.misses) if (self.hits + self.misses) > 0 else 0
            }

class QdrantClientPool:
    """Pool of Qdrant clients for connection reuse and concurrency control."""
    
    def __init__(self, host: str, port: int, max_clients: int = 10, timeout: float = 10.0):
        """
        Initialize client pool.
        
        Args:
            host: Qdrant server host
            port: Qdrant server port
            max_clients: Maximum number of clients in pool
            timeout: Timeout for client operations
        """
        self.host = host
        self.port = port
        self.max_clients = max_clients
        self.timeout = timeout
        self.clients = []
        self.lock = Lock()
        
        # Create initial clients
        for _ in range(max_clients):
            self.clients.append(self._create_client())
    
    def _create_client(self) -> QdrantClient:
        """Create a new Qdrant client."""
        return QdrantClient(
            host=self.host, 
            port=self.port,
            timeout=self.timeout,
            prefer_grpc=True  # Use gRPC for better performance
        )
    
    def get_client(self) -> QdrantClient:
        """Get client from pool."""
        with self.lock:
            if not self.clients:
                # All clients are in use, create a new one
                return self._create_client()
            
            # Get client from pool
            return self.clients.pop()
    
    def release_client(self, client: QdrantClient) -> None:
        """Return client to pool."""
        with self.lock:
            if len(self.clients) < self.max_clients:
                self.clients.append(client)
            # If pool is full, client will be garbage collected

class VectorRepository:
    """Repository for working with Qdrant vector database with caching and improved performance."""
    
    def __init__(self, host: str, port: int, cache_size: int = 1000, cache_ttl: int = 3600, 
                max_clients: int = 10, timeout: float = 10.0, max_workers: int = 4):
        """
        Initialize repository.
        
        Args:
            host: Qdrant server host
            port: Qdrant server port
            cache_size: Size of search cache
            cache_ttl: Time to live for cache entries in seconds
            max_clients: Maximum number of Qdrant clients in pool
            timeout: Timeout for Qdrant operations
            max_workers: Maximum number of worker threads
        """
        # Initialize client pool
        self.client_pool = QdrantClientPool(
            host=host, 
            port=port,
            max_clients=max_clients,
            timeout=timeout
        )
        
        # Create a dedicated client for common operations
        self.client = QdrantClient(host=host, port=port, timeout=timeout)
        
        # Create cache
        self.cache = VectorCache(max_size=cache_size, ttl=cache_ttl)
        
        # Create thread pool for parallel operations
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=max_workers)
        
        # Track known collections to avoid repeated checks
        self.known_collections: Set[str] = set()
        self.known_collections_lock = Lock()
    
    def _is_collection_known(self, name: str) -> bool:
        """Check if collection is known."""
        with self.known_collections_lock:
            return name in self.known_collections
    
    def _add_known_collection(self, name: str) -> None:
        """Add collection to known collections."""
        with self.known_collections_lock:
            self.known_collections.add(name)
    
    def _remove_known_collection(self, name: str) -> None:
        """Remove collection from known collections."""
        with self.known_collections_lock:
            self.known_collections.discard(name)
    
    def create_collection(self, name: str, vector_size: int = 1536) -> None:
        """
        Create a new collection with optimized configuration.
        
        Args:
            name: Collection name
            vector_size: Vector dimension
        """
        # Check if collection exists in our cache first
        if self._is_collection_known(name):
            return
        
        # Get client from pool
        client = self.client_pool.get_client()
        
        try:
            # Check if collection exists
            collections = client.get_collections().collections
            collection_names = [collection.name for collection in collections]
            
            if name in collection_names:
                self._add_known_collection(name)
                return  # Collection already exists
            
            # Create new collection with optimized configuration
            client.create_collection(
                collection_name=name,
                vectors_config=VectorParams(
                    size=vector_size,
                    distance=Distance.COSINE
                ),
                optimizers_config=models.OptimizersConfigDiff(
                    indexing_threshold=20000,  # Index after 20k vectors for better performance
                    memmap_threshold=2_000_000  # Use memory mapping for large collections
                ),
                hnsw_config=models.HnswConfigDiff(
                    m=16,  # Higher M value for more accurate search
                    ef_construct=200,  # Higher ef_construct for better index quality
                    full_scan_threshold=10000  # Use full scan for smaller collections
                ),
                quantization_config=models.ScalarQuantization(
                    scalar=models.ScalarQuantizationConfig(
                        type=models.ScalarType.INT8,
                        always_ram=True
                    )
                ) if vector_size >= 512 else None  # Use quantization for large vectors
            )
            
            self._add_known_collection(name)
            
        finally:
            # Return client to pool
            self.client_pool.release_client(client)
    
    def delete_collection(self, name: str) -> None:
        """
        Delete collection.
        
        Args:
            name: Collection name
        """
        # Use the common client for this simple operation
        # Check if collection exists
        collections = self.client.get_collections().collections
        collection_names = [collection.name for collection in collections]
        
        if name in collection_names:
            self.client.delete_collection(collection_name=name)
            self._remove_known_collection(name)
            
            # Clear cache entries related to this collection
            self.cache.clear()  # TODO: implement selective clearing
    
    def add_vector(self, collection: str, id: str, vector: List[float], metadata: Dict[str, Any]) -> None:
        """
        Add vector to collection.
        
        Args:
            collection: Collection name
            id: Vector ID
            vector: Vector
            metadata: Metadata
        """
        # Create collection if it doesn't exist
        if not self._is_collection_known(collection):
            try:
                self.create_collection(name=collection, vector_size=len(vector))
            except Exception as e:
                logger.warning(f"Error creating collection {collection}: {str(e)}")
        
        # Get client from pool
        client = self.client_pool.get_client()
        
        try:
            # Add vector
            client.upsert(
                collection_name=collection,
                points=[
                    PointStruct(
                        id=id,
                        vector=vector,
                        payload=metadata
                    )
                ]
            )
            
            # Clear cache entries related to this collection
            self.cache.clear()  # TODO: implement selective clearing
            
        finally:
            # Return client to pool
            self.client_pool.release_client(client)
    
    def add_vectors_batch(self, collection: str, vectors: List[Tuple[str, List[float], Dict[str, Any]]]) -> None:
        """
        Add multiple vectors to collection in batch.
        
        Args:
            collection: Collection name
            vectors: List of tuples (id, vector, metadata)
        """
        if not vectors:
            return
        
        # Create collection if it doesn't exist
        if not self._is_collection_known(collection):
            vector_size = len(vectors[0][1])
            try:
                self.create_collection(name=collection, vector_size=vector_size)
            except Exception as e:
                logger.warning(f"Error creating collection {collection}: {str(e)}")
        
        # Get client from pool
        client = self.client_pool.get_client()
        
        try:
            # Prepare points
            points = [
                PointStruct(
                    id=id,
                    vector=vector,
                    payload=metadata
                )
                for id, vector, metadata in vectors
            ]
            
            # Add vectors in batch
            client.upsert(
                collection_name=collection,
                points=points
            )
            
            # Clear cache entries related to this collection
            self.cache.clear()  # TODO: implement selective clearing
            
        finally:
            # Return client to pool
            self.client_pool.release_client(client)
    
    def delete_vector(self, collection: str, id: str) -> None:
        """
        Delete vector from collection.
        
        Args:
            collection: Collection name
            id: Vector ID
        """
        # Check if collection exists in our cache
        if not self._is_collection_known(collection):
            # Check if collection exists in Qdrant
            collections = self.client.get_collections().collections
            collection_names = [collection.name for collection in collections]
            
            if collection not in collection_names:
                return  # Collection doesn't exist
            
            self._add_known_collection(collection)
        
        # Use common client for this simple operation
        self.client.delete(
            collection_name=collection,
            points_selector=HasIdCondition(
                has_id=[id]
            )
        )
        
        # Clear cache entries related to this vector
        self.cache.clear()  # TODO: implement selective clearing
    
    def search(self, collection: str, query_vector: List[float], limit: int = 5, 
              filter_condition: Optional[Dict[str, Any]] = None) -> List[SearchResult]:
        """
        Search for nearest vectors with caching.
        
        Args:
            collection: Collection name
            query_vector: Query vector
            limit: Maximum number of results
            filter_condition: Filter condition for search
            
        Returns:
            List of search results
        """
        # Check if collection exists in our cache
        if not self._is_collection_known(collection):
            # Check if collection exists in Qdrant
            collections = self.client.get_collections().collections
            collection_names = [collection.name for collection in collections]
            
            if collection not in collection_names:
                return []  # Collection doesn't exist
            
            self._add_known_collection(collection)
        
        # Check cache
        cached_results = self.cache.get(collection, query_vector, limit, filter_condition)
        if cached_results is not None:
            return cached_results
        
        # Get client from pool
        client = self.client_pool.get_client()
        
        try:
            # Create filter if provided
            search_filter = None
            if filter_condition:
                must_conditions = []
                
                for key, value in filter_condition.items():
                    if isinstance(value, (dict, Dict)):
                        # Handle range conditions
                        if 'gt' in value or 'gte' in value or 'lt' in value or 'lte' in value:
                            range_condition = Range(
                                key=key,
                                gt=value.get('gt'),
                                gte=value.get('gte'),
                                lt=value.get('lt'),
                                lte=value.get('lte')
                            )
                            must_conditions.append(range_condition)
                    else:
                        # Handle exact match
                        match_condition = FieldCondition(
                            key=key,
                            match=MatchValue(value=value)
                        )
                        must_conditions.append(match_condition)
                
                search_filter = Filter(
                    must=must_conditions
                )
            
            # Set higher ef parameter for more accurate search
            search_params = models.SearchParams(
                hnsw_ef=128,
                exact=False
            )
            
            # Perform search
            search_results = client.search(
                collection_name=collection,
                query_vector=query_vector,
                limit=limit,
                query_filter=search_filter,
                search_params=search_params
            )
            
            # Convert results
            results = []
            for result in search_results:
                results.append(SearchResult(
                    id=result.id,
                    score=result.score,
                    metadata=result.payload
                ))
            
            # Cache results
            self.cache.set(collection, query_vector, limit, filter_condition, results)
            
            return results
            
        except Exception as e:
            logger.error(f"Error searching in collection {collection}: {str(e)}")
            return []
            
        finally:
            # Return client to pool
            self.client_pool.release_client(client)
    
    async def search_async(self, collection: str, query_vector: List[float], limit: int = 5, 
                         filter_condition: Optional[Dict[str, Any]] = None) -> List[SearchResult]:
        """
        Search for nearest vectors asynchronously.
        
        Args:
            collection: Collection name
            query_vector: Query vector
            limit: Maximum number of results
            filter_condition: Filter condition for search
            
        Returns:
            List of search results
        """
        # Check cache
        cached_results = self.cache.get(collection, query_vector, limit, filter_condition)
        if cached_results is not None:
            return cached_results
        
        # Run search in thread pool
        loop = asyncio.get_event_loop()
        results = await loop.run_in_executor(
            self.executor,
            lambda: self.search(collection, query_vector, limit, filter_condition)
        )
        
        return results
    
    async def batch_search(self, collection: str, query_vectors: List[List[float]], limit: int = 5,
                         filter_condition: Optional[Dict[str, Any]] = None) -> List[List[SearchResult]]:
        """
        Search for nearest vectors for multiple queries in parallel.
        
        Args:
            collection: Collection name
            query_vectors: List of query vectors
            limit: Maximum number of results per query
            filter_condition: Filter condition for search
            
        Returns:
            List of search results for each query
        """
        # Create tasks for each query
        tasks = [
            self.search_async(collection, query_vector, limit, filter_condition)
            for query_vector in query_vectors
        ]
        
        # Wait for all searches to complete
        return await asyncio.gather(*tasks)
    
    def list_collections(self) -> List[Dict[str, Any]]:
        """
        Get list of all collections.
        
        Returns:
            List of collection information
        """
        # Use common client for this simple operation
        collections = self.client.get_collections().collections
        result = []
        
        # Update known collections
        with self.known_collections_lock:
            self.known_collections = set(collection.name for collection in collections)
        
        for collection in collections:
            # Get collection info
            try:
                collection_info = self.client.get_collection(collection_name=collection.name)
                
                # Get point count
                collection_count = self.client.count(
                    collection_name=collection.name,
                    count_filter=None
                )
                
                result.append({
                    "name": collection.name,
                    "document_count": collection_count.count,
                    "vector_dimension": collection_info.config.params.vectors.size
                })
            except Exception as e:
                logger.error(f"Error getting info for collection {collection.name}: {str(e)}")
        
        return result
    
    def get_collection_info(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a specific collection.
        
        Args:
            name: Collection name
            
        Returns:
            Collection information or None if collection doesn't exist
        """
        try:
            # Get collection info
            collection_info = self.client.get_collection(collection_name=name)
            
            # Get point count
            collection_count = self.client.count(
                collection_name=name,
                count_filter=None
            )
            
            return {
                "name": name,
                "document_count": collection_count.count,
                "vector_dimension": collection_info.config.params.vectors.size,
                "config": {
                    "distance": str(collection_info.config.params.vectors.distance),
                    "on_disk": collection_info.config.params.vectors.on_disk,
                    "has_hnsw_index": collection_info.has_hnsw_index
                }
            }
        except Exception as e:
            logger.error(f"Error getting info for collection {name}: {str(e)}")
            return None
    
    def clear_cache(self) -> None:
        """Clear search cache."""
        self.cache.clear()
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return self.cache.get_stats()
