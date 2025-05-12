"""
Configuration for pytest.
"""
import os
import tempfile
import shutil
import pytest
from pathlib import Path
import logging

from app.config.config_loader import get_config, ConfigLoader
from app.domain.models.document import Document, DocumentMetadata, DocumentChunk
from app.domain.services.text_splitter import TextSplitter
from app.domain.services.language_detector import LanguageDetector
from app.domain.services.translation_service import TranslationService
from app.domain.services.embedding_generator import EmbeddingGenerator
from app.domain.services.multilingual_embedding_generator import MultilingualEmbeddingGenerator
from app.infrastructure.repositories.document_repository import DocumentRepository, FileSystemBackend, SQLiteBackend
from app.infrastructure.repositories.vector_repository import VectorRepository, SearchResult

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@pytest.fixture
def temp_directory():
    """Create a temporary directory for tests."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)

@pytest.fixture
def test_config():
    """Load test configuration."""
    # Override environment to use test config
    os.environ["APP_ENV"] = "test"
    
    # Create new config loader
    config_loader = ConfigLoader()
    config = config_loader.load()
    
    yield config
    
    # Reset environment
    if "APP_ENV" in os.environ:
        del os.environ["APP_ENV"]

@pytest.fixture
def document_metadata():
    """Create a sample document metadata."""
    return DocumentMetadata(
        source="test",
        collection="test_collection",
        language="en",
        title="Test Document",
        author="Test Author",
        additional_metadata={
            "tags": ["test", "sample"],
            "category": "test_data"
        }
    )

@pytest.fixture
def sample_document(document_metadata):
    """Create a sample document."""
    doc = Document(
        id="test_doc_1",
        content="This is a test document content. It contains multiple sentences. This is for testing purposes.",
        metadata=document_metadata
    )
    
    # Add sample chunks
    doc.add_chunk(
        chunk_id="test_doc_1_0",
        chunk_content="This is a test document content.",
        language="en"
    )
    
    doc.add_chunk(
        chunk_id="test_doc_1_1",
        chunk_content="It contains multiple sentences.",
        language="en"
    )
    
    doc.add_chunk(
        chunk_id="test_doc_1_2",
        chunk_content="This is for testing purposes.",
        language="en"
    )
    
    return doc

@pytest.fixture
def text_splitter():
    """Create a text splitter instance."""
    return TextSplitter()

@pytest.fixture
def language_detector():
    """Create a language detector instance."""
    return LanguageDetector()

@pytest.fixture
def translation_service():
    """Create a translation service with mock implementation."""
    class MockTranslationService(TranslationService):
        def __init__(self):
            self.enabled = True
            self.translation_models = {
                ('en', 'ru'): 'mock-model',
                ('ru', 'en'): 'mock-model'
            }
            self.cache = {}
        
        def translate(self, text: str, source_lang: str, target_lang: str) -> str:
            if source_lang == target_lang:
                return text
                
            # Simple mock translation for testing
            if source_lang == 'en' and target_lang == 'ru':
                return f"RU({text})"
            elif source_lang == 'ru' and target_lang == 'en':
                return f"EN({text})"
            else:
                return text
    
    return MockTranslationService()

@pytest.fixture
def document_repository(temp_directory):
    """Create a document repository instance using the file system backend."""
    return DocumentRepository(storage_path=temp_directory)

@pytest.fixture
def document_repository_sqlite(temp_directory):
    """Create a document repository instance using the SQLite backend."""
    return DocumentRepository(storage_path=temp_directory, use_sqlite=True)

@pytest.fixture
def mock_embedding_generator():
    """Create a mock embedding generator."""
    class MockEmbeddingGenerator:
        def generate(self, text: str) -> List[float]:
            # Generate deterministic fake embeddings based on text length
            return [float(len(text) % 10)] * 5
            
        def generate_batch(self, texts: List[str]) -> List[List[float]]:
            return [self.generate(text) for text in texts]
    
    return MockEmbeddingGenerator()

@pytest.fixture
def mock_vector_repository():
    """Create a mock vector repository."""
    class MockVectorRepository:
        def __init__(self):
            self.collections = {}
            self.vectors = {}
        
        def create_collection(self, name: str, vector_size: int = 5) -> None:
            self.collections[name] = {"vector_size": vector_size, "count": 0}
            self.vectors[name] = {}
        
        def add_vector(self, collection: str, id: str, vector: List[float], metadata: Dict[str, Any]) -> None:
            if collection not in self.collections:
                self.create_collection(collection, len(vector))
            
            self.vectors[collection][id] = (vector, metadata)
            self.collections[collection]["count"] += 1
        
        def search(self, collection: str, query_vector: List[float], limit: int = 5, 
                  filter_condition: Optional[Dict[str, Any]] = None) -> List[SearchResult]:
            if collection not in self.collections:
                return []
            
            results = []
            
            for id, (vector, metadata) in self.vectors[collection].items():
                # Simple similarity score based on first element
                score = 1.0 - abs(vector[0] - query_vector[0]) / 10.0
                results.append(SearchResult(id=id, score=score, metadata=metadata))
            
            # Sort by score
            results.sort(key=lambda x: x.score, reverse=True)
            
            # Apply limit
            return results[:limit]
        
        def list_collections(self) -> List[Dict[str, Any]]:
            return [
                {
                    "name": name,
                    "document_count": info["count"],
                    "vector_dimension": info["vector_size"]
                }
                for name, info in self.collections.items()
            ]
    
    return MockVectorRepository()
