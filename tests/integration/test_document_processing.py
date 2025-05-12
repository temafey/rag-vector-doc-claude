"""
Integration tests for document processing flow.
"""
import pytest
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from app.domain.models.document import Document, DocumentMetadata
from app.domain.services.text_splitter import TextSplitter
from app.domain.services.embedding_generator import EmbeddingGenerator
from app.domain.services.language_detector import LanguageDetector
from app.infrastructure.repositories.document_repository import DocumentRepository
from app.infrastructure.repositories.vector_repository import VectorRepository
from app.application.commands.document_commands import AddDocumentCommand, AddDocumentResult
from app.application.handlers.document_handlers import AddDocumentCommandHandler

class TestDocumentProcessing:
    """Integration tests for document processing flow."""
    
    @pytest.fixture
    def mock_embedding_generator(self):
        """Mock embedding generator."""
        mock = MagicMock(spec=EmbeddingGenerator)
        mock.generate.return_value = [0.1, 0.2, 0.3, 0.4, 0.5]
        return mock
    
    @pytest.fixture
    def command_handler(self, temp_directory, mock_embedding_generator):
        """Create AddDocumentCommandHandler with dependencies."""
        # Create repositories
        document_repository = DocumentRepository(storage_path=os.path.join(temp_directory, "documents"))
        
        # Create mock vector repository
        vector_repository = MagicMock(spec=VectorRepository)
        
        # Create services
        text_splitter = TextSplitter()
        language_detector = LanguageDetector()
        
        # Create handler
        return AddDocumentCommandHandler(
            document_repository=document_repository,
            vector_repository=vector_repository,
            text_splitter=text_splitter,
            embedding_generator=mock_embedding_generator,
            language_detector=language_detector
        )
    
    def test_add_document_command_flow(self, command_handler):
        """Test complete flow of adding a document."""
        # Create command
        command = AddDocumentCommand(
            id="test_doc_1",
            content="This is a test document for integration testing. It contains multiple sentences that will be split into chunks.",
            metadata={"title": "Test Document", "category": "integration_test"},
            collection="test_collection",
            chunk_size=50,
            chunk_overlap=10
        )
        
        # Execute command
        result = command_handler.handle(command)
        
        # Check result
        assert isinstance(result, AddDocumentResult)
        assert result.document_id == command.id
        assert result.chunk_count > 1  # Should have multiple chunks
        
        # Verify document was saved in repository
        doc = command_handler.document_repository.get_by_id(command.id)
        assert doc is not None
        assert doc.id == command.id
        assert doc.content == command.content
        assert len(doc.chunks) == result.chunk_count
        
        # Verify vector repository was called for each chunk
        assert command_handler.vector_repository.add_vector.call_count == result.chunk_count
    
    def test_language_detection_flow(self, command_handler):
        """Test language detection during document processing."""
        # Create command with mixed language
        command = AddDocumentCommand(
            id="test_doc_lang",
            content="This is English text. Это русский текст.",
            metadata={"title": "Mixed Language Document"},
            collection="test_collection"
        )
        
        # Mock language detector to track calls
        original_detect = command_handler.language_detector.detect
        detect_calls = []
        
        def mock_detect(text):
            detect_calls.append(text)
            return original_detect(text)
            
        command_handler.language_detector.detect = mock_detect
        
        # Execute command
        result = command_handler.handle(command)
        
        # Verify language detection was called
        assert len(detect_calls) >= 1
        
        # Verify document was saved with language info
        doc = command_handler.document_repository.get_by_id(command.id)
        assert doc.metadata.language is not None
        
        # Restore original method
        command_handler.language_detector.detect = original_detect
    
    def test_document_chunking_flow(self, command_handler):
        """Test document chunking with different parameters."""
        # Create base content
        paragraph = "This is a paragraph with multiple sentences. " * 10
        content = "\n\n".join([paragraph for _ in range(5)])
        
        # Test with different chunk sizes
        chunk_sizes = [50, 100, 200]
        chunk_counts = []
        
        for chunk_size in chunk_sizes:
            command = AddDocumentCommand(
                id=f"test_doc_chunk_{chunk_size}",
                content=content,
                metadata={"title": f"Chunk Test {chunk_size}"},
                collection="test_collection",
                chunk_size=chunk_size,
                chunk_overlap=20
            )
            
            result = command_handler.handle(command)
            chunk_counts.append(result.chunk_count)
        
        # Verify smaller chunk size produces more chunks
        assert chunk_counts[0] > chunk_counts[1] > chunk_counts[2]
        
        # Verify all documents were processed
        for chunk_size in chunk_sizes:
            doc = command_handler.document_repository.get_by_id(f"test_doc_chunk_{chunk_size}")
            assert doc is not None
