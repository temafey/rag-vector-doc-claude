"""
Tests for DocumentRepository.
"""
import pytest
import os
import json
import sqlite3
from pathlib import Path

from app.domain.models.document import Document, DocumentMetadata, DocumentChunk
from app.infrastructure.repositories.document_repository import (
    DocumentRepository, FileSystemBackend, SQLiteBackend
)

class TestDocumentRepository:
    """Test cases for DocumentRepository."""
    
    def test_save_and_get_document(self, document_repository, sample_document):
        """Test saving and retrieving a document."""
        # Save document
        document_repository.save(sample_document)
        
        # Retrieve document
        retrieved_document = document_repository.get_by_id(sample_document.id)
        
        # Check document properties
        assert retrieved_document is not None
        assert retrieved_document.id == sample_document.id
        assert retrieved_document.content == sample_document.content
        assert retrieved_document.metadata.source == sample_document.metadata.source
        assert retrieved_document.metadata.collection == sample_document.metadata.collection
        
        # Check chunks
        assert len(retrieved_document.chunks) == len(sample_document.chunks)
        for i, chunk in enumerate(sample_document.chunks):
            retrieved_chunk = retrieved_document.chunks[i]
            assert retrieved_chunk.id == chunk.id
            assert retrieved_chunk.content == chunk.content
    
    def test_delete_document(self, document_repository, sample_document):
        """Test deleting a document."""
        # Save document
        document_repository.save(sample_document)
        
        # Verify document exists
        assert document_repository.get_by_id(sample_document.id) is not None
        
        # Delete document
        document_repository.delete(sample_document.id)
        
        # Verify document was deleted
        assert document_repository.get_by_id(sample_document.id) is None
    
    def test_list_all_documents(self, document_repository, sample_document):
        """Test listing all documents."""
        # Create multiple documents
        docs = []
        for i in range(3):
            doc_id = f"test_doc_{i}"
            metadata = DocumentMetadata(
                source="test",
                collection="test_collection",
                language="en",
                title=f"Test Document {i}"
            )
            doc = Document(
                id=doc_id,
                content=f"Content of document {i}",
                metadata=metadata
            )
            docs.append(doc)
            document_repository.save(doc)
        
        # List all documents
        all_docs = document_repository.list_all()
        
        # Check correct number of documents
        assert len(all_docs) == 3
        
        # Check all documents are present
        doc_ids = [doc.id for doc in all_docs]
        for doc in docs:
            assert doc.id in doc_ids
    
    def test_caching(self, document_repository, sample_document):
        """Test document caching."""
        # Save document
        document_repository.save(sample_document)
        
        # Get document twice to hit cache
        doc1 = document_repository.get_by_id(sample_document.id)
        doc2 = document_repository.get_by_id(sample_document.id)
        
        # Verify both are the same object (from cache)
        assert doc1 is doc2
    
    @pytest.mark.parametrize("use_sqlite", [False, True])
    def test_repository_backends(self, temp_directory, sample_document, use_sqlite):
        """Test both FileSystem and SQLite backends."""
        # Create repository with specified backend
        repo = DocumentRepository(storage_path=temp_directory, use_sqlite=use_sqlite)
        
        # Save document
        repo.save(sample_document)
        
        # Verify correct backend is used
        if use_sqlite:
            # Check SQLite file exists
            db_path = os.path.join(temp_directory, "documents.db")
            assert os.path.exists(db_path)
            
            # Check document is in database
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM documents WHERE id = ?", (sample_document.id,))
            result = cursor.fetchone()
            conn.close()
            
            assert result is not None
            assert result[0] == sample_document.id
        else:
            # Check JSON file exists
            file_path = os.path.join(temp_directory, f"{sample_document.id}.json")
            assert os.path.exists(file_path)
            
            # Check file contains correct document
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                assert data["id"] == sample_document.id
    
    def test_get_by_metadata(self, document_repository, sample_document):
        """Test getting documents by metadata filter."""
        # Save document with specific metadata
        sample_document.metadata.additional_metadata["category"] = "test_category"
        sample_document.metadata.additional_metadata["tag"] = "important"
        document_repository.save(sample_document)
        
        # Add another document with different metadata
        other_doc = Document(
            id="other_doc",
            content="Other document content",
            metadata=DocumentMetadata(
                source="test",
                collection="test_collection",
                language="en",
                additional_metadata={"category": "other_category"}
            )
        )
        document_repository.save(other_doc)
        
        # Filter by metadata
        docs, total = document_repository.get_by_metadata(
            filters={"category": "test_category", "tag": "important"}
        )
        
        # Verify correct filtering
        assert total == 1
        assert len(docs) == 1
        assert docs[0]["id"] == sample_document.id
        
        # Filter with no matches
        docs, total = document_repository.get_by_metadata(
            filters={"category": "non_existent"}
        )
        
        assert total == 0
        assert len(docs) == 0
