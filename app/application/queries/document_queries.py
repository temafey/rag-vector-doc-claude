"""
Queries for document retrieval and search.
"""
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

class SearchQuery(BaseModel):
    """Query to search documents."""
    query_text: str
    collection: str = "default"
    limit: int = 5
    target_language: Optional[str] = None  # Desired response language

@dataclass
class SearchSource:
    """Source in search results."""
    id: str
    title: str
    content: str
    metadata: Dict[str, Any]
    score: float

@dataclass
class SearchResult:
    """Result of SearchQuery execution."""
    response: str
    sources: List[SearchSource]
    query_language: str  # Detected query language
    response_language: str  # Response language

class GetDocumentByIdQuery(BaseModel):
    """Query to get document by ID."""
    document_id: str
    collection: str = "default"

@dataclass
class DocumentResult:
    """Result of GetDocumentByIdQuery execution."""
    document: Optional[Any]  # Using Any as placeholder, in reality it's Document

class ListCollectionsQuery(BaseModel):
    """Query to list all collections."""
    pass

@dataclass
class CollectionInfo:
    """Collection information."""
    name: str
    document_count: int
    vector_dimension: int

@dataclass
class ListCollectionsResult:
    """Result of ListCollectionsQuery execution."""
    collections: List[CollectionInfo]

class GetSimilarDocumentsQuery(BaseModel):
    """Query to find similar documents to reference text."""
    reference_text: str
    collection: str = "default"
    limit: int = 5
    exclude_ids: List[str] = []

@dataclass
class SimilarDocumentsResult:
    """Result of GetSimilarDocumentsQuery execution."""
    documents: List[SearchSource]

class GetDocumentsByFilterQuery(BaseModel):
    """Query to get documents by metadata filter."""
    filter: Dict[str, Any]
    collection: str = "default"
    limit: int = 10
    offset: int = 0

@dataclass
class DocumentsFilterResult:
    """Result of GetDocumentsByFilterQuery execution."""
    documents: List[Dict[str, Any]]
    total: int
