"""
Domain models for documents, chunks, and metadata.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
import datetime

@dataclass
class DocumentMetadata:
    """Document metadata."""
    source: str
    collection: str
    language: str = "auto"  # Document language (auto = auto-detection)
    title: Optional[str] = None
    author: Optional[str] = None
    created_at: datetime.datetime = field(default_factory=datetime.datetime.now)
    additional_metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert metadata to dictionary.
        
        Returns:
            Dictionary representation of metadata
        """
        result = {
            "source": self.source,
            "collection": self.collection,
            "language": self.language,
            "created_at": self.created_at.isoformat()
        }
        
        if self.title:
            result["title"] = self.title
        
        if self.author:
            result["author"] = self.author
        
        # Add additional metadata
        result.update(self.additional_metadata)
        
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DocumentMetadata':
        """
        Create metadata from dictionary.
        
        Args:
            data: Dictionary with metadata
            
        Returns:
            DocumentMetadata instance
        """
        # Extract required fields
        source = data.pop("source")
        collection = data.pop("collection")
        
        # Extract optional fields
        language = data.pop("language", "auto")
        title = data.pop("title", None)
        author = data.pop("author", None)
        
        # Process created_at
        created_at_str = data.pop("created_at", None)
        created_at = datetime.datetime.fromisoformat(created_at_str) if created_at_str else datetime.datetime.now()
        
        # Remaining keys are considered additional metadata
        additional_metadata = data
        
        return cls(
            source=source,
            collection=collection,
            language=language,
            title=title,
            author=author,
            created_at=created_at,
            additional_metadata=additional_metadata
        )

@dataclass
class DocumentChunk:
    """Document chunk."""
    id: str
    content: str
    index: int
    language: str = "auto"  # Chunk language (auto = auto-detection)
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class Document:
    """Document in RAG system."""
    id: str
    content: str
    metadata: DocumentMetadata
    chunks: List[DocumentChunk] = field(default_factory=list)
    
    def add_chunk(self, chunk_id: str, chunk_content: str, language: str = "auto") -> None:
        """
        Add chunk to document.
        
        Args:
            chunk_id: Chunk ID
            chunk_content: Chunk content
            language: Chunk language
        """
        chunk = DocumentChunk(
            id=chunk_id,
            content=chunk_content,
            index=len(self.chunks),
            language=language
        )
        self.chunks.append(chunk)
