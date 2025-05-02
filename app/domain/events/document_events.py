"""
Domain events related to documents.
"""
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

class DocumentIndexedEvent(BaseModel):
    """Event generated when a document is indexed."""
    document_id: str
    collection: str
    chunk_count: int
    language: Optional[str] = None

class ChunksGeneratedEvent(BaseModel):
    """Event generated when chunks are created from a document."""
    document_id: str
    chunk_count: int

class EmbeddingsGeneratedEvent(BaseModel):
    """Event generated when embeddings are created for document chunks."""
    document_id: str
    chunk_ids: List[str]
    collection: str

class DocumentDeletedEvent(BaseModel):
    """Event generated when a document is deleted."""
    document_id: str
    collection: str

class CollectionCreatedEvent(BaseModel):
    """Event generated when a collection is created."""
    name: str
    vector_size: int

class CollectionDeletedEvent(BaseModel):
    """Event generated when a collection is deleted."""
    name: str
