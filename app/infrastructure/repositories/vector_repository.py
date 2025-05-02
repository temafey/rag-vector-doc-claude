"""
Repository for vector database operations.
"""
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from qdrant_client import QdrantClient
from qdrant_client.http import models

@dataclass
class SearchResult:
    """Search result from vector database."""
    id: str
    score: float
    metadata: Dict[str, Any]

class VectorRepository:
    """Repository for working with Qdrant vector database."""
    
    def __init__(self, host: str, port: int):
        """
        Initialize repository.
        
        Args:
            host: Qdrant server host
            port: Qdrant server port
        """
        self.client = QdrantClient(host=host, port=port)
    
    def create_collection(self, name: str, vector_size: int = 1536) -> None:
        """
        Create a new collection.
        
        Args:
            name: Collection name
            vector_size: Vector dimension
        """
        # Check if collection exists
        collections = self.client.get_collections().collections
        collection_names = [collection.name for collection in collections]
        
        if name in collection_names:
            return  # Collection already exists
        
        # Create new collection
        self.client.create_collection(
            collection_name=name,
            vectors_config=models.VectorParams(
                size=vector_size,
                distance=models.Distance.COSINE
            )
        )
    
    def delete_collection(self, name: str) -> None:
        """
        Delete collection.
        
        Args:
            name: Collection name
        """
        # Check if collection exists
        collections = self.client.get_collections().collections
        collection_names = [collection.name for collection in collections]
        
        if name in collection_names:
            self.client.delete_collection(collection_name=name)
    
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
        try:
            self.create_collection(name=collection, vector_size=len(vector))
        except Exception as e:
            # Ignore error if collection already exists
            pass
        
        # Add vector
        self.client.upsert(
            collection_name=collection,
            points=[
                models.PointStruct(
                    id=id,
                    vector=vector,
                    payload=metadata
                )
            ]
        )
    
    def delete_vector(self, collection: str, id: str) -> None:
        """
        Delete vector from collection.
        
        Args:
            collection: Collection name
            id: Vector ID
        """
        # Check if collection exists
        collections = self.client.get_collections().collections
        collection_names = [collection.name for collection in collections]
        
        if collection in collection_names:
            self.client.delete(
                collection_name=collection,
                points_selector=models.PointIdsList(
                    points=[id]
                )
            )
    
    def search(self, collection: str, query_vector: List[float], limit: int = 5, 
              filter_condition: Optional[Dict[str, Any]] = None) -> List[SearchResult]:
        """
        Search for nearest vectors.
        
        Args:
            collection: Collection name
            query_vector: Query vector
            limit: Maximum number of results
            filter_condition: Filter condition for search
            
        Returns:
            List of search results
        """
        # Check if collection exists
        collections = self.client.get_collections().collections
        collection_names = [collection.name for collection in collections]
        
        if collection not in collection_names:
            return []  # Collection doesn't exist
        
        # Create filter if provided
        search_filter = None
        if filter_condition:
            search_filter = models.Filter(
                must=[
                    models.FieldCondition(
                        key=key,
                        match=models.MatchValue(value=value)
                    )
                    for key, value in filter_condition.items()
                ]
            )
        
        # Perform search
        search_results = self.client.search(
            collection_name=collection,
            query_vector=query_vector,
            limit=limit,
            query_filter=search_filter
        )
        
        # Convert results
        results = []
        for result in search_results:
            results.append(SearchResult(
                id=result.id,
                score=result.score,
                metadata=result.payload
            ))
        
        return results
    
    def list_collections(self) -> List[Dict[str, Any]]:
        """
        Get list of all collections.
        
        Returns:
            List of collection information
        """
        collections = self.client.get_collections().collections
        result = []
        
        for collection in collections:
            # Get collection info
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
        
        return result
