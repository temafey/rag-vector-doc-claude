"""
Repository for document storage and retrieval with caching and multiple storage backends.
"""
from typing import Dict, Optional, List, Any, Tuple
import json
import os
import sqlite3
import pickle
from threading import Lock
from functools import lru_cache
from contextlib import contextmanager
from app.domain.models.document import Document, DocumentMetadata, DocumentChunk

class StorageBackend:
    """Interface for document storage backends."""
    
    def save(self, document_id: str, document_data: Dict[str, Any]) -> None:
        """Save document data."""
        raise NotImplementedError
    
    def load(self, document_id: str) -> Optional[Dict[str, Any]]:
        """Load document data."""
        raise NotImplementedError
    
    def delete(self, document_id: str) -> None:
        """Delete document."""
        raise NotImplementedError
    
    def list_documents(self) -> List[str]:
        """List all document IDs."""
        raise NotImplementedError
    
    def get_metadata(self, document_id: str) -> Optional[Dict[str, Any]]:
        """Get only document metadata for efficiency."""
        raise NotImplementedError

class FileSystemBackend(StorageBackend):
    """File system storage backend."""
    
    def __init__(self, storage_path: str):
        """Initialize backend."""
        self.storage_path = storage_path
        os.makedirs(storage_path, exist_ok=True)
    
    def _get_document_path(self, document_id: str) -> str:
        """Get path to document file."""
        return os.path.join(self.storage_path, f"{document_id}.json")
    
    def save(self, document_id: str, document_data: Dict[str, Any]) -> None:
        """Save document data to file."""
        document_path = self._get_document_path(document_id)
        with open(document_path, "w", encoding="utf-8") as f:
            json.dump(document_data, f, ensure_ascii=False, indent=2)
    
    def load(self, document_id: str) -> Optional[Dict[str, Any]]:
        """Load document data from file."""
        document_path = self._get_document_path(document_id)
        
        if not os.path.exists(document_path):
            return None
            
        with open(document_path, "r", encoding="utf-8") as f:
            return json.load(f)
    
    def delete(self, document_id: str) -> None:
        """Delete document file."""
        document_path = self._get_document_path(document_id)
        if os.path.exists(document_path):
            os.remove(document_path)
    
    def list_documents(self) -> List[str]:
        """List all document IDs based on filenames."""
        document_ids = []
        for filename in os.listdir(self.storage_path):
            if filename.endswith(".json"):
                document_ids.append(filename[:-5])  # Remove .json extension
        return document_ids
    
    def get_metadata(self, document_id: str) -> Optional[Dict[str, Any]]:
        """Get document metadata from file."""
        document_data = self.load(document_id)
        if document_data:
            return document_data.get("metadata")
        return None

class SQLiteBackend(StorageBackend):
    """SQLite storage backend for better performance with many documents."""
    
    def __init__(self, db_path: str):
        """Initialize backend."""
        self.db_path = db_path
        self.lock = Lock()  # Для многопоточной безопасности
        
        # Create database and tables if not exists
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS documents (
                id TEXT PRIMARY KEY,
                content TEXT,
                metadata TEXT
            )
            ''')
            
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS chunks (
                id TEXT PRIMARY KEY,
                document_id TEXT,
                content TEXT,
                index_num INTEGER,
                language TEXT,
                metadata TEXT,
                FOREIGN KEY (document_id) REFERENCES documents (id) ON DELETE CASCADE
            )
            ''')
            
            # Enable foreign keys
            cursor.execute("PRAGMA foreign_keys = ON")
            conn.commit()
    
    @contextmanager
    def _get_connection(self):
        """Get SQLite connection with context manager."""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            yield conn
        finally:
            if conn:
                conn.close()
    
    def save(self, document_id: str, document_data: Dict[str, Any]) -> None:
        """Save document data to SQLite."""
        with self.lock, self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Insert or update document
            cursor.execute(
                "INSERT OR REPLACE INTO documents (id, content, metadata) VALUES (?, ?, ?)",
                (
                    document_id, 
                    document_data["content"], 
                    json.dumps(document_data["metadata"])
                )
            )
            
            # Delete existing chunks
            cursor.execute("DELETE FROM chunks WHERE document_id = ?", (document_id,))
            
            # Insert chunks
            for chunk in document_data["chunks"]:
                cursor.execute(
                    "INSERT INTO chunks (id, document_id, content, index_num, language, metadata) VALUES (?, ?, ?, ?, ?, ?)",
                    (
                        chunk["id"],
                        document_id,
                        chunk["content"],
                        chunk["index"],
                        chunk.get("language", "auto"),
                        json.dumps(chunk.get("metadata", {}))
                    )
                )
            
            conn.commit()
    
    def load(self, document_id: str) -> Optional[Dict[str, Any]]:
        """Load document data from SQLite."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Get document
            cursor.execute("SELECT * FROM documents WHERE id = ?", (document_id,))
            document_row = cursor.fetchone()
            
            if not document_row:
                return None
            
            # Get chunks
            cursor.execute("SELECT * FROM chunks WHERE document_id = ? ORDER BY index_num", (document_id,))
            chunk_rows = cursor.fetchall()
            
            # Construct document data
            document_data = {
                "id": document_row["id"],
                "content": document_row["content"],
                "metadata": json.loads(document_row["metadata"]),
                "chunks": [
                    {
                        "id": chunk["id"],
                        "content": chunk["content"],
                        "index": chunk["index_num"],
                        "language": chunk["language"],
                        "metadata": json.loads(chunk["metadata"])
                    }
                    for chunk in chunk_rows
                ]
            }
            
            return document_data
    
    def delete(self, document_id: str) -> None:
        """Delete document from SQLite."""
        with self.lock, self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM documents WHERE id = ?", (document_id,))
            conn.commit()
    
    def list_documents(self) -> List[str]:
        """List all document IDs from SQLite."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM documents")
            return [row["id"] for row in cursor.fetchall()]
    
    def get_metadata(self, document_id: str) -> Optional[Dict[str, Any]]:
        """Get only document metadata from SQLite."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT metadata FROM documents WHERE id = ?", (document_id,))
            row = cursor.fetchone()
            if row:
                return json.loads(row["metadata"])
            return None
    
    def get_documents_by_metadata(self, filters: Dict[str, Any], limit: int = 100, offset: int = 0) -> Tuple[List[Dict[str, Any]], int]:
        """
        Get documents matching metadata filters with pagination.
        Returns tuple of (documents, total_count)
        """
        query_conditions = []
        query_params = []
        
        # Build SQL query based on filters
        for key, value in filters.items():
            # Each condition checks if the JSON has the key with specified value
            # This is a simplified approach and may not work for complex nested metadata
            query_conditions.append(f"json_extract(metadata, '$.{key}') = ?")
            query_params.append(value)
        
        where_clause = " AND ".join(query_conditions) if query_conditions else "1=1"
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Get total count
            cursor.execute(f"SELECT COUNT(*) as count FROM documents WHERE {where_clause}", query_params)
            total_count = cursor.fetchone()["count"]
            
            # Get paginated results
            cursor.execute(
                f"SELECT id, content, metadata FROM documents WHERE {where_clause} LIMIT ? OFFSET ?",
                query_params + [limit, offset]
            )
            
            documents = []
            for row in cursor.fetchall():
                documents.append({
                    "id": row["id"],
                    "content": row["content"][:200] + "..." if len(row["content"]) > 200 else row["content"],
                    "metadata": json.loads(row["metadata"])
                })
            
            return documents, total_count

class DocumentRepository:
    """Repository for working with documents with caching and multiple backends."""
    
    def __init__(self, storage_path: str, use_sqlite: bool = False, cache_size: int = 100):
        """
        Initialize repository.
        
        Args:
            storage_path: Path to directory for document storage
            use_sqlite: Whether to use SQLite backend for storage
            cache_size: Size of the LRU cache
        """
        self.storage_path = storage_path
        
        # Set up storage backend
        if use_sqlite:
            db_path = os.path.join(storage_path, "documents.db")
            self.backend = SQLiteBackend(db_path)
        else:
            self.backend = FileSystemBackend(storage_path)
        
        # Enable document caching
        self._setup_cache(cache_size)
    
    def _setup_cache(self, cache_size: int):
        """Set up LRU cache for documents."""
        self._document_cache = {}
        self._get_by_id_cached = lru_cache(maxsize=cache_size)(self._get_by_id_uncached)
    
    def save(self, document: Document) -> None:
        """
        Save document.
        
        Args:
            document: Document to save
        """
        # Convert document to dict
        document_dict = {
            "id": document.id,
            "content": document.content,
            "metadata": document.metadata.to_dict(),
            "chunks": [
                {
                    "id": chunk.id,
                    "content": chunk.content,
                    "index": chunk.index,
                    "language": chunk.language,
                    "metadata": chunk.metadata
                }
                for chunk in document.chunks
            ]
        }
        
        # Save to backend
        self.backend.save(document.id, document_dict)
        
        # Update cache
        self._update_cache(document)
    
    def _update_cache(self, document: Document):
        """Update document in cache."""
        self._document_cache[document.id] = document
        
        # Clear the LRU cache to ensure it gets the updated document
        if hasattr(self, '_get_by_id_cached'):
            self._get_by_id_cached.cache_clear()
    
    def get_by_id(self, document_id: str) -> Optional[Document]:
        """
        Get document by ID with caching.
        
        Args:
            document_id: Document ID
            
        Returns:
            Document or None if document not found
        """
        # Check in-memory cache first
        if document_id in self._document_cache:
            return self._document_cache[document_id]
            
        # Use LRU cached method
        return self._get_by_id_cached(document_id)
    
    def _get_by_id_uncached(self, document_id: str) -> Optional[Document]:
        """
        Internal method to get document by ID without using the cache.
        
        Args:
            document_id: Document ID
            
        Returns:
            Document or None if document not found
        """
        # Load from backend
        document_dict = self.backend.load(document_id)
        
        if not document_dict:
            return None
        
        # Create DocumentMetadata object
        metadata = DocumentMetadata.from_dict(document_dict["metadata"])
        
        # Create Document object
        document = Document(
            id=document_dict["id"],
            content=document_dict["content"],
            metadata=metadata
        )
        
        # Add chunks
        for chunk_dict in document_dict["chunks"]:
            chunk = DocumentChunk(
                id=chunk_dict["id"],
                content=chunk_dict["content"],
                index=chunk_dict["index"],
                language=chunk_dict.get("language", "auto"),
                metadata=chunk_dict.get("metadata", {})
            )
            document.chunks.append(chunk)
        
        # Update cache
        self._document_cache[document_id] = document
        
        return document
    
    def delete(self, document_id: str) -> None:
        """
        Delete document.
        
        Args:
            document_id: Document ID
        """
        # Delete from backend
        self.backend.delete(document_id)
        
        # Remove from cache
        if document_id in self._document_cache:
            del self._document_cache[document_id]
            
        # Clear LRU cache
        if hasattr(self, '_get_by_id_cached'):
            self._get_by_id_cached.cache_clear()
    
    def list_all(self) -> List[Document]:
        """
        Get list of all documents.
        
        Returns:
            List of documents
        """
        documents = []
        
        # Get all document IDs from backend
        document_ids = self.backend.list_documents()
        
        # Load each document
        for document_id in document_ids:
            document = self.get_by_id(document_id)
            if document:
                documents.append(document)
        
        return documents
    
    def get_by_metadata(self, filters: Dict[str, Any], limit: int = 100, offset: int = 0) -> Tuple[List[Dict[str, Any]], int]:
        """
        Get documents by metadata filters with pagination.
        
        Args:
            filters: Dictionary of metadata filters (key-value pairs)
            limit: Maximum number of results to return
            offset: Pagination offset
            
        Returns:
            Tuple of (documents list, total count)
        """
        # Use SQLite backend's efficient filtering if available
        if isinstance(self.backend, SQLiteBackend):
            return self.backend.get_documents_by_metadata(filters, limit, offset)
        
        # Fallback for file system backend - less efficient
        documents = []
        total_count = 0
        
        for document_id in self.backend.list_documents():
            metadata = self.backend.get_metadata(document_id)
            
            if not metadata:
                continue
                
            # Check if document matches all filters
            match = True
            for key, value in filters.items():
                if key not in metadata or metadata[key] != value:
                    match = False
                    break
            
            if match:
                total_count += 1
                
                # Apply pagination
                if total_count > offset and len(documents) < limit:
                    document_data = self.backend.load(document_id)
                    documents.append({
                        "id": document_id,
                        "content": document_data["content"][:200] + "..." if len(document_data["content"]) > 200 else document_data["content"],
                        "metadata": metadata
                    })
        
        return documents, total_count
