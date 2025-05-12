"""
Integration tests for search flow.
"""
import pytest
from unittest.mock import MagicMock, patch
import asyncio
import os

from app.domain.models.document import Document, DocumentMetadata
from app.domain.services.multilingual_embedding_generator import MultilingualEmbeddingGenerator
from app.domain.services.response_generator import ResponseGenerator
from app.domain.services.language_detector import LanguageDetector
from app.domain.services.translation_service import TranslationService
from app.infrastructure.repositories.document_repository import DocumentRepository
from app.infrastructure.repositories.vector_repository import VectorRepository, SearchResult
from app.application.queries.document_queries import (
    SearchQuery, SearchResult as QuerySearchResult, SearchSource
)
from app.application.handlers.query_handlers import SearchQueryHandler

class TestSearchFlow:
    """Integration tests for search flow."""
    
    @pytest.fixture
    def mock_embedding_generator(self):
        """Mock embedding generator."""
        mock = MagicMock(spec=MultilingualEmbeddingGenerator)
        mock.generate.return_value = [0.1, 0.2, 0.3, 0.4, 0.5]
        return mock
    
    @pytest.fixture
    def mock_vector_repository(self):
        """Mock vector repository."""
        mock = MagicMock(spec=VectorRepository)
        
        # Setup search to return test results
        mock.search.return_value = [
            SearchResult(
                id="chunk1",
                score=0.95,
                metadata={
                    "document_id": "doc1",
                    "content": "This is the first chunk of content.",
                    "language": "en",
                    "title": "Test Document 1"
                }
            ),
            SearchResult(
                id="chunk2",
                score=0.85,
                metadata={
                    "document_id": "doc2",
                    "content": "This is the second chunk of content.",
                    "language": "en",
                    "title": "Test Document 2"
                }
            )
        ]
        
        return mock
    
    @pytest.fixture
    def mock_document_repository(self):
        """Mock document repository."""
        mock = MagicMock(spec=DocumentRepository)
        
        # Setup get_by_id to return test documents
        def get_by_id(doc_id):
            if doc_id == "doc1":
                return Document(
                    id="doc1",
                    content="Full content of document 1",
                    metadata=DocumentMetadata(
                        source="test",
                        collection="test_collection",
                        language="en",
                        title="Test Document 1"
                    )
                )
            elif doc_id == "doc2":
                return Document(
                    id="doc2",
                    content="Full content of document 2",
                    metadata=DocumentMetadata(
                        source="test",
                        collection="test_collection",
                        language="en",
                        title="Test Document 2"
                    )
                )
            return None
            
        mock.get_by_id.side_effect = get_by_id
        
        return mock
    
    @pytest.fixture
    def mock_response_generator(self):
        """Mock response generator."""
        mock = MagicMock(spec=ResponseGenerator)
        mock.generate.return_value = "Generated response based on context"
        return mock
    
    @pytest.fixture
    def query_handler(self, mock_embedding_generator, mock_vector_repository, 
                     mock_document_repository, mock_response_generator):
        """Create SearchQueryHandler with dependencies."""
        # Create other required services
        language_detector = LanguageDetector()
        translation_service = TranslationService()
        
        # Create handler
        return SearchQueryHandler(
            document_repository=mock_document_repository,
            vector_repository=mock_vector_repository,
            embedding_generator=mock_embedding_generator,
            response_generator=mock_response_generator,
            language_detector=language_detector,
            translation_service=translation_service
        )
    
    def test_search_query_flow(self, query_handler):
        """Test complete flow of search query."""
        # Create query
        query = SearchQuery(
            query_text="Test search query",
            collection="test_collection",
            limit=5
        )
        
        # Execute query
        result = query_handler.handle(query)
        
        # Check result structure
        assert isinstance(result, QuerySearchResult)
        assert result.response == "Generated response based on context"
        assert len(result.sources) == 2
        assert result.sources[0].id == "chunk1"
        assert result.sources[1].id == "chunk2"
        
        # Verify embedding generator was called
        query_handler.embedding_generator.generate.assert_called_once_with(query.query_text)
        
        # Verify vector repository was called
        query_handler.vector_repository.search.assert_called_once()
        
        # Verify response generator was called
        query_handler.response_generator.generate.assert_called_once()
    
    def test_search_with_language_detection(self, query_handler):
        """Test search with language detection."""
        # Create query with mixed language
        query = SearchQuery(
            query_text="English query with русский текст",
            collection="test_collection",
            limit=5
        )
        
        # Spy on language detector
        original_detect = query_handler.language_detector.detect
        detect_calls = []
        
        def mock_detect(text):
            detect_calls.append(text)
            return original_detect(text)
            
        query_handler.language_detector.detect = mock_detect
        
        # Execute query
        result = query_handler.handle(query)
        
        # Verify language detection was called
        assert len(detect_calls) >= 1
        assert detect_calls[0] == query.query_text
        
        # Verify language was detected and set in result
        assert result.query_language is not None
        
        # Restore original method
        query_handler.language_detector.detect = original_detect
    
    def test_search_with_translation(self, query_handler):
        """Test search with translation."""
        # Setup translation service with tracking
        query_handler.translation_service = MagicMock(spec=TranslationService)
        query_handler.translation_service.translate.return_value = "Translated content"
        query_handler.translation_service.enabled = True
        
        # Override vector repository to return different language
        query_handler.vector_repository.search.return_value = [
            SearchResult(
                id="chunk1",
                score=0.95,
                metadata={
                    "document_id": "doc1",
                    "content": "Это контент на русском языке.",
                    "language": "ru",
                    "title": "Test Document 1"
                }
            )
        ]
        
        # Create query with target language
        query = SearchQuery(
            query_text="Test query",
            collection="test_collection",
            limit=5,
            target_language="en"  # Request English response
        )
        
        # Execute query
        result = query_handler.handle(query)
        
        # Verify translation was called for Russian content
        query_handler.translation_service.translate.assert_called_with(
            "Это контент на русском языке.", "ru", "en"
        )
        
        # Verify translated content was used for response generation
        query_handler.response_generator.generate.assert_called_once()
        context_arg = query_handler.response_generator.generate.call_args[0][1]
        assert "Translated content" in context_arg[0]
