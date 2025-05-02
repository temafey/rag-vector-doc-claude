"""
Repository for document storage and retrieval.
"""
from typing import Dict, Optional, List
import json
import os
from app.domain.models.document import Document, DocumentMetadata, DocumentChunk

class DocumentRepository:
    """Repository for working with documents."""
    
    def __init__(self, storage_path: str):
        """
        Initialize repository.
        
        Args:
            storage_path: Path to directory for document storage
        """
        self.storage_path = storage_path
        os.makedirs(storage_path, exist_ok=True)
    
    def _get_document_path(self, document_id: str) -> str:
        """Get path to document file."""
        return os.path.join(self.storage_path, f"{document_id}.json")
    
    def save(self, document: Document) -> None:
        """
        Save document.
        
        Args:
            document: Document to save
        """
        document_path = self._get_document_path(document.id)
        
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
        
        # Save document to file
        with open(document_path, "w", encoding="utf-8") as f:
            json.dump(document_dict, f, ensure_ascii=False, indent=2)
    
    def get_by_id(self, document_id: str) -> Optional[Document]:
        """
        Get document by ID.
        
        Args:
            document_id: Document ID
            
        Returns:
            Document or None if document not found
        """
        document_path = self._get_document_path(document_id)
        
        # Check if file exists
        if not os.path.exists(document_path):
            return None
        
        # Load document from file
        with open(document_path, "r", encoding="utf-8") as f:
            document_dict = json.load(f)
        
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
        
        return document
    
    def delete(self, document_id: str) -> None:
        """
        Delete document.
        
        Args:
            document_id: Document ID
        """
        document_path = self._get_document_path(document_id)
        
        # Check if file exists
        if os.path.exists(document_path):
            os.remove(document_path)
    
    def list_all(self) -> List[Document]:
        """
        Get list of all documents.
        
        Returns:
            List of documents
        """
        documents = []
        
        # Iterate through all files in directory
        for filename in os.listdir(self.storage_path):
            if filename.endswith(".json"):
                document_id = filename[:-5]  # Remove .json extension
                document = self.get_by_id(document_id)
                if document:
                    documents.append(document)
        
        return documents
