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
from app.infrastructure.logging import (
    get_logger, 
    log_execution_time, 
    log_errors,
    operation_context
)
from app.config.config_loader import get_config
import time

class SearchQueryHandler(QueryHandler[SearchQuery, SearchResult]):
    """Handler for SearchQuery with comprehensive logging."""
    
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
        self.logger = get_logger("query_processing.search")
    
    @log_execution_time(operation_name="search_query", include_args=False)
    @log_errors(reraise=True)
    def handle(self, query: SearchQuery) -> SearchResult:
        """Handle SearchQuery with comprehensive logging."""
        
        # Create query ID for tracking
        query_id = f"search_{int(time.time() * 1000)}"
        
        # Log search operation start
        self.logger.log_business_event(
            event="search_query_started",
            entity_type="search_query",
            entity_id=query_id,
            query_text=query.query_text[:100] + "..." if len(query.query_text) > 100 else query.query_text,
            collection=query.collection,
            limit=query.limit,
            target_language=query.target_language,
            query_length=len(query.query_text)
        )
        
        start_time = time.time()
        
        try:
            # Step 1: Language Detection
            self.logger.debug("Starting language detection", context={
                "query_id": query_id,
                "query_length": len(query.query_text)
            })
            
            lang_start = time.time()
            query_language, confidence = self.language_detector.detect(query.query_text)
            lang_duration = time.time() - lang_start
            
            self.logger.info("Language detection completed", context={
                "query_id": query_id,
                "detected_language": query_language,
                "confidence": confidence,
                "detection_duration_ms": lang_duration * 1000
            })
            
            # Step 2: Determine Target Language
            target_language = query.target_language or query_language
            
            if target_language != query_language:
                self.logger.info("Target language differs from query language", context={
                    "query_id": query_id,
                    "query_language": query_language,
                    "target_language": target_language
                })
            
            # Step 3: Generate Query Embedding
            self.logger.debug("Starting query embedding generation", context={
                "query_id": query_id,
                "query_language": query_language
            })
            
            embed_start = time.time()
            query_embedding = self.embedding_generator.generate(query.query_text)
            embed_duration = time.time() - embed_start
            
            self.logger.info("Query embedding generated", context={
                "query_id": query_id,
                "embedding_dimensions": len(query_embedding),
                "embedding_duration_ms": embed_duration * 1000
            })
            
            # Step 4: Vector Search
            self.logger.debug("Starting vector search", context={
                "query_id": query_id,
                "collection": query.collection,
                "limit": query.limit
            })
            
            search_start = time.time()
            search_results = self.vector_repository.search(
                collection=query.collection,
                query_vector=query_embedding,
                limit=query.limit
            )
            search_duration = time.time() - search_start
            
            self.logger.info("Vector search completed", context={
                "query_id": query_id,
                "results_found": len(search_results),
                "search_duration_ms": search_duration * 1000,
                "collection": query.collection
            })
            
            # Step 5: Process Search Results
            context_preparation_start = time.time()
            context_chunks = []
            sources = []
            translation_count = 0
            
            for idx, result in enumerate(search_results):
                chunk_content = result.metadata.get("content", "")
                chunk_language = result.metadata.get("language", "en")
                
                self.logger.debug("Processing search result", context={
                    "query_id": query_id,
                    "result_index": idx,
                    "result_id": result.id,
                    "relevance_score": result.score,
                    "chunk_language": chunk_language,
                    "chunk_length": len(chunk_content)
                })
                
                # Translation if needed
                if (chunk_language != target_language and 
                    self.config["translation"].get("enabled", True)):
                    
                    translate_start = time.time()
                    translated_content = self.translation_service.translate(
                        chunk_content, chunk_language, target_language
                    )
                    translate_duration = time.time() - translate_start
                    
                    context_chunks.append(translated_content)
                    translation_count += 1
                    
                    self.logger.debug("Content translated", context={
                        "query_id": query_id,
                        "result_index": idx,
                        "from_language": chunk_language,
                        "to_language": target_language,
                        "translation_duration_ms": translate_duration * 1000
                    })
                else:
                    context_chunks.append(chunk_content)
                
                # Get document info
                document_id = result.metadata.get("document_id", "")
                document = None
                if document_id:
                    document = self.document_repository.get_by_id(document_id)
                
                # Determine title
                title = (document.metadata.title if document and document.metadata.title 
                        else result.metadata.get("title", "Unknown document"))
                
                # Add to sources
                sources.append(SearchSource(
                    id=result.id,
                    title=title,
                    content=chunk_content,
                    metadata=result.metadata,
                    score=result.score
                ))
            
            context_preparation_duration = time.time() - context_preparation_start
            
            self.logger.info("Search results processed", context={
                "query_id": query_id,
                "context_chunks": len(context_chunks),
                "translations_performed": translation_count,
                "processing_duration_ms": context_preparation_duration * 1000,
                "avg_relevance_score": sum(s.score for s in sources) / len(sources) if sources else 0
            })
            
            # Step 6: Generate Response
            self.logger.debug("Starting response generation", context={
                "query_id": query_id,
                "context_chunks": len(context_chunks),
                "target_language": target_language
            })
            
            response_start = time.time()
            response = self.response_generator.generate(
                query=query.query_text,
                context=context_chunks,
                language=target_language
            )
            response_duration = time.time() - response_start
            
            self.logger.info("Response generated", context={
                "query_id": query_id,
                "response_length": len(response),
                "generation_duration_ms": response_duration * 1000,
                "target_language": target_language
            })
            
            # Create final result
            result = SearchResult(
                response=response,
                sources=sources,
                query_language=query_language,
                response_language=target_language
            )
            
            # Log successful completion with full metrics
            total_duration = time.time() - start_time
            
            self.logger.log_business_event(
                event="search_query_completed",
                entity_type="search_query",
                entity_id=query_id,
                query_language=query_language,
                target_language=target_language,
                results_found=len(search_results),
                sources_returned=len(sources),
                translations_performed=translation_count,
                response_length=len(response),
                total_duration_ms=total_duration * 1000
            )
            
            # Log detailed performance metrics
            self.logger.log_performance(
                operation="search_query",
                duration=total_duration,
                query_length=len(query.query_text),
                language_detection_ms=lang_duration * 1000,
                embedding_generation_ms=embed_duration * 1000,
                vector_search_ms=search_duration * 1000,
                context_processing_ms=context_preparation_duration * 1000,
                response_generation_ms=response_duration * 1000,
                results_found=len(search_results),
                translations_performed=translation_count,
                avg_relevance_score=sum(s.score for s in sources) / len(sources) if sources else 0
            )
            
            return result
            
        except Exception as e:
            # Log search failure
            error_duration = time.time() - start_time
            self.logger.log_business_event(
                event="search_query_failed",
                entity_type="search_query",
                entity_id=query_id,
                error_type=type(e).__name__,
                error_message=str(e),
                duration_ms=error_duration * 1000,
                query_text=query.query_text[:100] + "..." if len(query.query_text) > 100 else query.query_text
            )
            raise

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
    """Handler for GetSimilarDocumentsQuery with comprehensive logging."""
    
    def __init__(
        self,
        document_repository: DocumentRepository,
        vector_repository: VectorRepository,
        embedding_generator: MultilingualEmbeddingGenerator
    ):
        self.document_repository = document_repository
        self.vector_repository = vector_repository
        self.embedding_generator = embedding_generator
        self.logger = get_logger("query_processing.similar_documents")
    
    @log_execution_time(operation_name="similar_documents_query")
    @log_errors(reraise=True)
    def handle(self, query: GetSimilarDocumentsQuery) -> SimilarDocumentsResult:
        """Handle GetSimilarDocumentsQuery with comprehensive logging."""
        
        query_id = f"similar_{int(time.time() * 1000)}"
        
        # Log operation start
        self.logger.log_business_event(
            event="similar_documents_query_started",
            entity_type="similar_query",
            entity_id=query_id,
            reference_text_length=len(query.reference_text),
            collection=query.collection,
            limit=query.limit,
            exclude_ids_count=len(query.exclude_ids)
        )
        
        start_time = time.time()
        
        try:
            # Generate embedding for reference text
            embed_start = time.time()
            reference_embedding = self.embedding_generator.generate(query.reference_text)
            embed_duration = time.time() - embed_start
            
            self.logger.info("Reference embedding generated", context={
                "query_id": query_id,
                "embedding_dimensions": len(reference_embedding),
                "embedding_duration_ms": embed_duration * 1000
            })
            
            # Search similar vectors
            search_start = time.time()
            search_results = self.vector_repository.search(
                collection=query.collection,
                query_vector=reference_embedding,
                limit=query.limit
            )
            search_duration = time.time() - search_start
            
            self.logger.info("Similar vectors search completed", context={
                "query_id": query_id,
                "results_found": len(search_results),
                "search_duration_ms": search_duration * 1000
            })
            
            # Process results
            sources = []
            seen_document_ids = set()
            excluded_count = 0
            duplicate_count = 0
            
            for result in search_results:
                document_id = result.metadata.get("document_id", "")
                
                # Skip excluded IDs and already seen documents
                if document_id in query.exclude_ids:
                    excluded_count += 1
                    continue
                    
                if document_id in seen_document_ids:
                    duplicate_count += 1
                    continue
                    
                seen_document_ids.add(document_id)
                
                # Get document
                document = self.document_repository.get_by_id(document_id) if document_id else None
                
                # Determine title
                title = (document.metadata.title if document and document.metadata.title 
                        else result.metadata.get("title", "Unknown document"))
                
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
            
            # Log completion
            total_duration = time.time() - start_time
            
            self.logger.log_business_event(
                event="similar_documents_query_completed",
                entity_type="similar_query",
                entity_id=query_id,
                sources_returned=len(sources),
                excluded_count=excluded_count,
                duplicate_count=duplicate_count,
                total_duration_ms=total_duration * 1000
            )
            
            self.logger.log_performance(
                operation="similar_documents_query",
                duration=total_duration,
                reference_text_length=len(query.reference_text),
                embedding_duration_ms=embed_duration * 1000,
                search_duration_ms=search_duration * 1000,
                results_processed=len(search_results),
                sources_returned=len(sources),
                avg_similarity_score=sum(s.score for s in sources) / len(sources) if sources else 0
            )
            
            return SimilarDocumentsResult(documents=sources)
            
        except Exception as e:
            error_duration = time.time() - start_time
            self.logger.log_business_event(
                event="similar_documents_query_failed",
                entity_type="similar_query",
                entity_id=query_id,
                error_type=type(e).__name__,
                error_message=str(e),
                duration_ms=error_duration * 1000
            )
            raise

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
