"""
Commands for document management.
"""
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

class AddDocumentCommand(BaseModel):
    """Command to add document to collection."""
    id: str
    content: str
    metadata: Dict[str, Any] = {}
    collection: str = "default"
    chunk_size: int = 1000
    chunk_overlap: int = 200
    language: Optional[str] = None  # Document language (optional)

@dataclass
class AddDocumentResult:
    """Result of AddDocumentCommand execution."""
    document_id: str
    chunk_count: int

class AddFilesCommand(BaseModel):
    """Command to add files to collection."""
    files: List[str]
    collection: str = "default"
    metadata: Dict[str, Any] = {}
    chunk_size: int = 1000
    chunk_overlap: int = 200
    batch_size: int = 10
    language: Optional[str] = None  # Document language (optional)

@dataclass
class AddFilesResult:
    """Result of AddFilesCommand execution."""
    total_documents: int
    total_chunks: int

class DeleteDocumentCommand(BaseModel):
    """Command to delete document from collection."""
    document_id: str
    collection: str = "default"

class CreateCollectionCommand(BaseModel):
    """Command to create new collection."""
    name: str
    vector_size: int = 1536  # Default vector dimension for embeddings

class DeleteCollectionCommand(BaseModel):
    """Command to delete collection."""
    name: str

class UpdateDocumentLanguageCommand(BaseModel):
    """Command to update document language."""
    document_id: str
    language: str
    collection: str = "default"

class ReindexDocumentCommand(BaseModel):
    """Command to reindex document with new parameters."""
    document_id: str
    collection: str = "default"
    chunk_size: Optional[int] = None
    chunk_overlap: Optional[int] = None
    language: Optional[str] = None
