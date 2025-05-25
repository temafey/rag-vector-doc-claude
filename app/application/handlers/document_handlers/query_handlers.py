"""
Query handlers for document retrieval and search.
"""
from app.application.queries.document_queries import (
    SearchQuery, SearchResult, SearchSource,
    GetDocumentByIdQuery, DocumentResult,
    ListCollectionsQuery, ListCollectionsResult, CollectionInfo,
    GetSimilarDocumentsQuery, SimilarDocumentsResult,
    GetDocumentsByFilterQuery, DocumentsFilterResult
)
from app.domain.services.multilingual_embedding_generator import MultilingualEmbeddingGenerator
from app.domain.services.response_generator import ResponseGenerator
from app.domain.services.language_detector import LanguageDetector
from app.domain.services.translation_service import TranslationService
from app.infrastructure.repositories.document_repository import DocumentRepository
from app.infrastructure.repositories.vector_repository import VectorRepository
from app.infrastructure.query_bus import QueryHandler
from app.config.config_loader import get_config

class SearchQueryHandler(QueryHandler[SearchQuery, SearchResult]):
    """Handler for SearchQuery."""
    
    def __init__(
        self,
        document_repository: DocumentRepository,
        vector_repository: VectorRepository,
        embedding_generator: MultilingualEmbeddingGenerator,
        response_generator: ResponseGenerator,
        language_detector: LanguageDetector,
        translation_service: TranslationService
    ):
        self.document_repository = document_repository
        self.vector_repository = vector_repository
        self.embedding_generator = embedding_generator
        self.response_generator = response_generator
        self.language_detector = language_detector
        self.translation_service = translation_service
        self.config = get_config()
    
    def handle(self, query: SearchQuery) -> SearchResult:
        # Detect query language
        query_language, _ = self.language_detector.detect(query.query_text)
        
        # Determine target language for response
        target_language = query.target_language or query_language
        
        # Generate embedding for query
        query_embedding = self.embedding_generator.generate(query.query_text)
        
        # Search nearest vectors in Qdrant
        search_results = self.vector_repository.search(
            collection=query.collection,
            query_vector=query_embedding,
            limit=query.limit
        )
        
        # Prepare context for response generation
        context_chunks = []
        sources = []
        
        for result in search_results:
            chunk_content = result.metadata.get("content", "")
            chunk_language = result.metadata.get("language", "en")
            
            # If chunk language differs from target language, translate if enabled
            if chunk_language != target_language and self.config["translation"].get("enabled", True):
                translated_content = self.translation_service.translate(
                    chunk_content, chunk_language, target_language
                )
                context_chunks.append(translated_content)
            else:
                context_chunks.append(chunk_content)
            
            # Get document info
            document_id = result.metadata.get("document_id", "")
            document = self.document_repository.get_by_id(document_id) if document_id else None
            
            # Determine title
            title = document.metadata.title if document and document.metadata.title else result.metadata.get("title", "Unknown document")
            
            # Add to sources
            sources.append(SearchSource(
                id=result.id,
                title=title,
                content=chunk_content,
                metadata=result.metadata,
                score=result.score
            ))
        
        # Generate response based on retrieved context
        response = self.response_generator.generate(
            query=query.query_text,
            context=context_chunks,
            language=target_language
        )
        
        return SearchResult(
            response=response,
            sources=sources,
            query_language=query_language,
            response_language=target_language
        )

class GetDocumentByIdQueryHandler(QueryHandler[GetDocumentByIdQuery, DocumentResult]):
    """Handler for GetDocumentByIdQuery."""
    
    def __init__(self, document_repository: DocumentRepository):
        self.document_repository = document_repository
    
    def handle(self, query: GetDocumentByIdQuery) -> DocumentResult:
        document = self.document_repository.get_by_id(query.document_id)
        return DocumentResult(document=document)

class ListCollectionsQueryHandler(QueryHandler[ListCollectionsQuery, ListCollectionsResult]):
    """Handler for ListCollectionsQuery."""
    
    def __init__(self, vector_repository: VectorRepository):
        self.vector_repository = vector_repository
    
    def handle(self, query: ListCollectionsQuery) -> ListCollectionsResult:
        collections_info = self.vector_repository.list_collections()
        return ListCollectionsResult(
            collections=[
                CollectionInfo(
                    name=info["name"],
                    document_count=info["document_count"],
                    vector_dimension=info["vector_dimension"]
                )
                for info in collections_info
            ]
        )

class GetSimilarDocumentsQueryHandler(QueryHandler[GetSimilarDocumentsQuery, SimilarDocumentsResult]):
    """Handler for GetSimilarDocumentsQuery."""
    
    def __init__(
        self,
        document_repository: DocumentRepository,
        vector_repository: VectorRepository,
        embedding_generator: MultilingualEmbeddingGenerator
    ):
        self.document_repository = document_repository
        self.vector_repository = vector_repository
        self.embedding_generator = embedding_generator
    
    def handle(self, query: GetSimilarDocumentsQuery) -> SimilarDocumentsResult:
        # Generate embedding for reference text
        reference_embedding = self.embedding_generator.generate(query.reference_text)
        
        # Search similar vectors
        search_results = self.vector_repository.search(
            collection=query.collection,
            query_vector=reference_embedding,
            limit=query.limit
        )
        
        # Prepare results
        sources = []
        seen_document_ids = set()
        
        for result in search_results:
            document_id = result.metadata.get("document_id", "")
            
            # Skip excluded IDs and already seen documents
            if document_id in query.exclude_ids or document_id in seen_document_ids:
                continue
                
            seen_document_ids.add(document_id)
            
            # Get document
            document = self.document_repository.get_by_id(document_id) if document_id else None
            
            # Determine title
            title = document.metadata.title if document and document.metadata.title else result.metadata.get("title", "Unknown document")
            
            # Add to sources
            sources.append(SearchSource(
                id=document_id,
                title=title,
                content=result.metadata.get("content", ""),
                metadata=result.metadata,
                score=result.score
            ))
            
            # Limit results
            if len(sources) >= query.limit:
                break
        
        return SimilarDocumentsResult(documents=sources)

class GetDocumentsByFilterQueryHandler(QueryHandler[GetDocumentsByFilterQuery, DocumentsFilterResult]):
    """Handler for GetDocumentsByFilterQuery."""
    
    def __init__(
        self,
        document_repository: DocumentRepository,
        vector_repository: VectorRepository
    ):
        self.document_repository = document_repository
        self.vector_repository = vector_repository
    
    def handle(self, query: GetDocumentsByFilterQuery) -> DocumentsFilterResult:
        # This is a simplified implementation
        # In a real system, we'd use more sophisticated filtering in the vector database
        
        # Get all documents
        all_documents = self.document_repository.list_all()
        
        # Filter documents based on metadata
        filtered_docs = []
        
        for doc in all_documents:
            # Check if document belongs to the specified collection
            if doc.metadata.collection != query.collection:
                continue
                
            # Check if document matches all filter criteria
            matches = True
            for key, value in query.filter.items():
                # Check metadata fields
                if key in doc.metadata.to_dict():
                    if doc.metadata.to_dict()[key] != value:
                        matches = False
                        break
                else:
                    matches = False
                    break
                    
            if matches:
                # Convert to dict for response
                filtered_docs.append({
                    "id": doc.id,
                    "content": doc.content[:200] + "..." if len(doc.content) > 200 else doc.content,
                    "metadata": doc.metadata.to_dict(),
                    "chunks_count": len(doc.chunks)
                })
        
        # Apply pagination
        total = len(filtered_docs)
        paginated_docs = filtered_docs[query.offset:query.offset + query.limit]
        
        return DocumentsFilterResult(
            documents=paginated_docs,
            total=total
        )
