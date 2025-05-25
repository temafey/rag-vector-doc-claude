"""
Command handlers for document operations.
"""
from app.application.commands.document_commands import (
    AddDocumentCommand, AddDocumentResult,
    AddFilesCommand, AddFilesResult,
    DeleteDocumentCommand,
    CreateCollectionCommand,
    DeleteCollectionCommand,
    UpdateDocumentLanguageCommand,
    ReindexDocumentCommand
)
from app.domain.models.document import Document, DocumentMetadata
from app.domain.services.text_splitter import TextSplitter
from app.domain.services.embedding_generator import EmbeddingGenerator
from app.domain.services.multilingual_embedding_generator import MultilingualEmbeddingGenerator
from app.domain.services.language_detector import LanguageDetector
from app.infrastructure.repositories.document_repository import DocumentRepository
from app.infrastructure.repositories.vector_repository import VectorRepository
from app.infrastructure.command_bus import CommandHandler
from app.infrastructure.event_bus import event_bus
from app.domain.events.document_events import (
    DocumentIndexedEvent, 
    ChunksGeneratedEvent,
    EmbeddingsGeneratedEvent,
    DocumentDeletedEvent,
    CollectionCreatedEvent,
    CollectionDeletedEvent
)
from app.infrastructure.logging import (
    get_logger, 
    log_execution_time, 
    log_errors,
    ProgressTracker,
    BatchProgressLogger
)

from typing import List, Dict, Any
import os
import uuid
import time
from app.infrastructure.parsers.parser_factory import ParserFactory
from app.config.config_loader import get_config

class AddDocumentCommandHandler(CommandHandler[AddDocumentCommand, AddDocumentResult]):
    """Handler for AddDocumentCommand."""
    
    def __init__(
        self,
        document_repository: DocumentRepository,
        vector_repository: VectorRepository,
        text_splitter: TextSplitter,
        embedding_generator: MultilingualEmbeddingGenerator,
        language_detector: LanguageDetector
    ):
        self.document_repository = document_repository
        self.vector_repository = vector_repository
        self.text_splitter = text_splitter
        self.embedding_generator = embedding_generator
        self.language_detector = language_detector
        self.config = get_config()
        self.logger = get_logger("document_processing.add_document")
    
    @log_execution_time(operation_name="add_document", include_args=False)
    @log_errors(reraise=True)
    def handle(self, command: AddDocumentCommand) -> AddDocumentResult:
        """Handle AddDocumentCommand with comprehensive logging."""
        # Log operation start
        self.logger.log_business_event(
            event="document_add_started",
            entity_type="document",
            entity_id=command.id,
            collection=command.collection,
            content_length=len(command.content),
            chunk_size=command.chunk_size,
            chunk_overlap=command.chunk_overlap,
            language=command.language
        )
        
        start_time = time.time()
        
        try:
            # Step 1: Language Detection
            self.logger.info("Starting language detection", context={
                "document_id": command.id,
                "specified_language": command.language,
                "content_length": len(command.content)
            })
            
            document_language = command.language or "auto"
            if document_language == "auto":
                lang_start = time.time()
                document_language, confidence = self.language_detector.detect(command.content)
                lang_duration = time.time() - lang_start
                
                self.logger.info("Language detection completed", context={
                    "document_id": command.id,
                    "detected_language": document_language,
                    "confidence": confidence,
                    "detection_duration_ms": lang_duration * 1000
                })
            
            # Step 2: Create Document Metadata
            metadata = DocumentMetadata(
                source="api",
                collection=command.collection,
                language=document_language,
                **command.metadata
            )
            
            self.logger.debug("Document metadata created", context={
                "document_id": command.id,
                "metadata": metadata.to_dict()
            })
            
            # Step 3: Create Document
            document = Document(
                id=command.id,
                content=command.content,
                metadata=metadata
            )
            
            # Step 4: Text Splitting
            self.logger.info("Starting text splitting", context={
                "document_id": command.id,
                "chunk_size": command.chunk_size,
                "chunk_overlap": command.chunk_overlap,
                "content_length": len(command.content)
            })
            
            split_start = time.time()
            chunks = self.text_splitter.split_text(
                text=command.content,
                chunk_size=command.chunk_size,
                chunk_overlap=command.chunk_overlap
            )
            split_duration = time.time() - split_start
            
            self.logger.info("Text splitting completed", context={
                "document_id": command.id,
                "chunk_count": len(chunks),
                "split_duration_ms": split_duration * 1000,
                "avg_chunk_size": sum(len(chunk) for chunk in chunks) / len(chunks) if chunks else 0
            })
            
            # Step 5: Add Chunks to Document
            chunk_processing_start = time.time()
            for i, chunk_text in enumerate(chunks):
                chunk_id = f"{command.id}_{i}"
                
                # Detect chunk language if configured
                if self.config.get("languages", {}).get("detect_chunk_language", False):
                    chunk_language, _ = self.language_detector.detect(chunk_text)
                else:
                    chunk_language = document_language
                    
                document.add_chunk(
                    chunk_id=chunk_id, 
                    chunk_content=chunk_text,
                    language=chunk_language
                )
            
            chunk_processing_duration = time.time() - chunk_processing_start
            self.logger.debug("Chunk processing completed", context={
                "document_id": command.id,
                "chunks_processed": len(chunks),
                "processing_duration_ms": chunk_processing_duration * 1000
            })
            
            # Step 6: Save Document
            save_start = time.time()
            self.document_repository.save(document)
            save_duration = time.time() - save_start
            
            self.logger.info("Document saved to repository", context={
                "document_id": command.id,
                "save_duration_ms": save_duration * 1000
            })
            
            # Publish chunks generated event
            event_bus.publish(ChunksGeneratedEvent(
                document_id=document.id,
                chunk_count=len(document.chunks)
            ))
            
            # Step 7: Generate Embeddings
            self.logger.info("Starting embedding generation", context={
                "document_id": command.id,
                "chunk_count": len(document.chunks)
            })
            
            embedding_start = time.time()
            chunk_ids = []
            embedding_progress = ProgressTracker(
                total=len(document.chunks),
                operation_name=f"embedding_generation_doc_{command.id}",
                logger_name="document_processing.embeddings"
            )
            
            for chunk_idx, chunk in enumerate(document.chunks):
                chunk_embed_start = time.time()
                embedding = self.embedding_generator.generate(chunk.content)
                chunk_embed_duration = time.time() - chunk_embed_start
                
                chunk_ids.append(chunk.id)
                
                # Save embedding to vector storage
                self.vector_repository.add_vector(
                    collection=command.collection,
                    id=chunk.id,
                    vector=embedding,
                    metadata={
                        "document_id": document.id,
                        "chunk_index": chunk.index,
                        "content": chunk.content,
                        "language": chunk.language,
                        **metadata.to_dict()
                    }
                )
                
                # Update progress
                embedding_progress.update(
                    current_item=f"chunk_{chunk_idx}",
                )
                
                self.logger.debug("Chunk embedding completed", context={
                    "document_id": command.id,
                    "chunk_id": chunk.id,
                    "chunk_index": chunk_idx,
                    "embedding_duration_ms": chunk_embed_duration * 1000,
                    "embedding_dimensions": len(embedding)
                })
            
            embedding_duration = time.time() - embedding_start
            embedding_progress.complete(
                total_embeddings=len(chunk_ids),
                avg_embedding_time_ms=(embedding_duration / len(chunk_ids)) * 1000 if chunk_ids else 0
            )
            
            # Publish embeddings generated event
            event_bus.publish(EmbeddingsGeneratedEvent(
                document_id=document.id,
                chunk_ids=chunk_ids,
                collection=command.collection
            ))
            
            # Publish document indexed event
            event_bus.publish(DocumentIndexedEvent(
                document_id=document.id,
                collection=command.collection,
                chunk_count=len(document.chunks),
                language=document_language
            ))
            
            # Calculate final metrics
            total_duration = time.time() - start_time
            
            # Log successful completion
            self.logger.log_business_event(
                event="document_add_completed",
                entity_type="document",
                entity_id=command.id,
                collection=command.collection,
                chunk_count=len(document.chunks),
                total_duration_ms=total_duration * 1000,
                language=document_language,
                content_length=len(command.content)
            )
            
            self.logger.log_performance(
                operation="add_document",
                duration=total_duration,
                chunks_created=len(document.chunks),
                embeddings_generated=len(chunk_ids),
                content_length=len(command.content),
                chunks_per_second=len(document.chunks) / total_duration if total_duration > 0 else 0
            )
            
            return AddDocumentResult(
                document_id=document.id,
                chunk_count=len(document.chunks)
            )
            
        except Exception as e:
            # Log error with full context
            error_duration = time.time() - start_time
            self.logger.log_business_event(
                event="document_add_failed",
                entity_type="document",
                entity_id=command.id,
                collection=command.collection,
                error_type=type(e).__name__,
                error_message=str(e),
                duration_ms=error_duration * 1000
            )
            raise

class AddFilesCommandHandler(CommandHandler[AddFilesCommand, AddFilesResult]):
    """Handler for AddFilesCommand with comprehensive batch processing logging."""
    
    def __init__(
        self,
        document_repository: DocumentRepository,
        vector_repository: VectorRepository,
        text_splitter: TextSplitter,
        embedding_generator: MultilingualEmbeddingGenerator,
        language_detector: LanguageDetector,
        parser_factory: ParserFactory
    ):
        self.document_repository = document_repository
        self.vector_repository = vector_repository
        self.text_splitter = text_splitter
        self.embedding_generator = embedding_generator
        self.language_detector = language_detector
        self.parser_factory = parser_factory
        self.logger = get_logger("document_processing.add_files")
    
    @log_execution_time(operation_name="add_files_batch", include_args=False)
    @log_errors(reraise=True)
    def handle(self, command: AddFilesCommand) -> AddFilesResult:
        """Handle AddFilesCommand with comprehensive batch logging."""
        
        # Initialize batch logging
        batch_logger = BatchProgressLogger("add_files_batch", "document_processing.batch")
        
        # Log batch operation start
        self.logger.log_business_event(
            event="batch_file_processing_started",
            entity_type="file_batch",
            entity_id=f"batch_{int(time.time())}",
            file_count=len(command.files),
            collection=command.collection,
            chunk_size=command.chunk_size,
            chunk_overlap=command.chunk_overlap
        )
        
        batch_start_time = time.time()
        total_documents = 0
        total_chunks = 0
        processed_files = 0
        failed_files = 0
        file_processing_metrics = []
        
        # Setup progress tracking
        progress_tracker = ProgressTracker(
            total=len(command.files),
            operation_name="file_batch_processing",
            logger_name="document_processing.progress"
        )
        
        # Process each file
        for file_idx, file_path in enumerate(command.files):
            file_start_time = time.time()
            file_name = os.path.basename(file_path)
            
            batch_logger.log_batch_start(
                batch_id=f"file_{file_idx}",
                batch_size=1,
                file_path=file_path,
                file_name=file_name
            )
            
            try:
                # Get parser for file
                self.logger.debug("Getting parser for file", context={
                    "file_path": file_path,
                    "file_name": file_name,
                    "file_index": file_idx
                })
                
                parser = self.parser_factory.get_parser(file_path)
                
                # Parse file
                parse_start = time.time()
                parsed_documents = parser.parse(file_path)
                parse_duration = time.time() - parse_start
                
                self.logger.info("File parsed successfully", context={
                    "file_path": file_path,
                    "documents_found": len(parsed_documents),
                    "parse_duration_ms": parse_duration * 1000
                })
                
                # Process each document from the file
                file_documents = 0
                file_chunks = 0
                
                for doc_idx, parsed_doc in enumerate(parsed_documents):
                    doc_id = str(uuid.uuid4())
                    
                    # Prepare metadata
                    metadata = {
                        "source_file": file_name,
                        "file_type": os.path.splitext(file_name)[1][1:],
                        "file_index": file_idx,
                        "document_index": doc_idx,
                        **command.metadata
                    }
                    
                    if "metadata" in parsed_doc:
                        metadata.update(parsed_doc["metadata"])
                    
                    # Create add document command
                    add_doc_command = AddDocumentCommand(
                        id=doc_id,
                        content=parsed_doc["content"],
                        metadata=metadata,
                        collection=command.collection,
                        chunk_size=command.chunk_size,
                        chunk_overlap=command.chunk_overlap,
                        language=command.language
                    )
                    
                    # Process document
                    from app.infrastructure.command_bus import command_bus
                    result = command_bus.dispatch(add_doc_command)
                    
                    file_documents += 1
                    file_chunks += result.chunk_count
                    
                    self.logger.debug("Document processed from file", context={
                        "file_name": file_name,
                        "document_id": doc_id,
                        "document_index": doc_idx,
                        "chunk_count": result.chunk_count
                    })
                
                # Update totals
                total_documents += file_documents
                total_chunks += file_chunks
                processed_files += 1
                
                # Calculate file processing metrics
                file_duration = time.time() - file_start_time
                file_metrics = {
                    "file_name": file_name,
                    "file_index": file_idx,
                    "documents_processed": file_documents,
                    "chunks_created": file_chunks,
                    "processing_duration_ms": file_duration * 1000,
                    "documents_per_second": file_documents / file_duration if file_duration > 0 else 0
                }
                file_processing_metrics.append(file_metrics)
                
                # Log successful file processing
                batch_logger.log_batch_complete(
                    batch_id=f"file_{file_idx}",
                    items_processed=file_documents,
                    chunks_created=file_chunks,
                    **file_metrics
                )
                
                self.logger.info("File processing completed", context={
                    "file_name": file_name,
                    "file_index": file_idx,
                    "documents_processed": file_documents,
                    "chunks_created": file_chunks,
                    "processing_duration_ms": file_duration * 1000
                })
                
            except Exception as e:
                failed_files += 1
                file_duration = time.time() - file_start_time
                
                # Log file processing error
                batch_logger.log_batch_error(
                    batch_id=f"file_{file_idx}",
                    error=e,
                    file_name=file_name,
                    processing_duration_ms=file_duration * 1000
                )
                
                self.logger.error("File processing failed", context={
                    "file_path": file_path,
                    "file_name": file_name,
                    "file_index": file_idx,
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "processing_duration_ms": file_duration * 1000
                }, exc_info=True)
                
                # Continue processing other files
                continue
            
            finally:
                # Update progress
                progress_tracker.update(
                    current_item=file_name
                )
        
        # Complete progress tracking
        batch_duration = time.time() - batch_start_time
        progress_tracker.complete(
            files_processed=processed_files,
            files_failed=failed_files,
            total_documents=total_documents,
            total_chunks=total_chunks
        )
        
        # Log batch operation summary
        batch_summary = batch_logger.log_operation_summary()
        
        # Log business event for batch completion
        self.logger.log_business_event(
            event="batch_file_processing_completed",
            entity_type="file_batch",
            entity_id=f"batch_{int(batch_start_time)}",
            files_processed=processed_files,
            files_failed=failed_files,
            total_documents=total_documents,
            total_chunks=total_chunks,
            batch_duration_ms=batch_duration * 1000,
            success_rate=(processed_files / len(command.files)) * 100 if command.files else 0
        )
        
        # Log performance metrics
        self.logger.log_performance(
            operation="add_files_batch",
            duration=batch_duration,
            files_processed=processed_files,
            files_failed=failed_files,
            documents_created=total_documents,
            chunks_created=total_chunks,
            files_per_second=processed_files / batch_duration if batch_duration > 0 else 0,
            documents_per_second=total_documents / batch_duration if batch_duration > 0 else 0
        )
        
        return AddFilesResult(
            total_documents=total_documents,
            total_chunks=total_chunks
        )

class DeleteDocumentCommandHandler(CommandHandler[DeleteDocumentCommand, None]):
    """Handler for DeleteDocumentCommand with comprehensive logging."""
    
    def __init__(
        self,
        document_repository: DocumentRepository,
        vector_repository: VectorRepository
    ):
        self.document_repository = document_repository
        self.vector_repository = vector_repository
        self.logger = get_logger("document_processing.delete_document")
    
    @log_execution_time(operation_name="delete_document")
    @log_errors(reraise=True)
    def handle(self, command: DeleteDocumentCommand) -> None:
        """Handle DeleteDocumentCommand with comprehensive logging."""
        
        # Log operation start
        self.logger.log_business_event(
            event="document_delete_started",
            entity_type="document",
            entity_id=command.document_id,
            collection=command.collection
        )
        
        start_time = time.time()
        
        try:
            # Get document
            document = self.document_repository.get_by_id(command.document_id)
            if not document:
                self.logger.warning("Document not found for deletion", context={
                    "document_id": command.document_id,
                    "collection": command.collection
                })
                return
            
            chunk_count = len(document.chunks)
            self.logger.info("Document found for deletion", context={
                "document_id": command.document_id,
                "chunk_count": chunk_count,
                "collection": command.collection
            })
            
            # Delete vectors from Qdrant
            vector_delete_start = time.time()
            for chunk in document.chunks:
                self.vector_repository.delete_vector(
                    collection=command.collection,
                    id=chunk.id
                )
            vector_delete_duration = time.time() - vector_delete_start
            
            self.logger.info("Vectors deleted from collection", context={
                "document_id": command.document_id,
                "vectors_deleted": chunk_count,
                "vector_delete_duration_ms": vector_delete_duration * 1000
            })
            
            # Delete document from repository
            repo_delete_start = time.time()
            self.document_repository.delete(command.document_id)
            repo_delete_duration = time.time() - repo_delete_start
            
            self.logger.info("Document deleted from repository", context={
                "document_id": command.document_id,
                "repo_delete_duration_ms": repo_delete_duration * 1000
            })
            
            # Publish document deleted event
            event_bus.publish(DocumentDeletedEvent(
                document_id=command.document_id,
                collection=command.collection
            ))
            
            # Log successful completion
            total_duration = time.time() - start_time
            self.logger.log_business_event(
                event="document_delete_completed",
                entity_type="document",
                entity_id=command.document_id,
                collection=command.collection,
                chunks_deleted=chunk_count,
                total_duration_ms=total_duration * 1000
            )
            
            self.logger.log_performance(
                operation="delete_document",
                duration=total_duration,
                chunks_deleted=chunk_count
            )
            
        except Exception as e:
            error_duration = time.time() - start_time
            self.logger.log_business_event(
                event="document_delete_failed",
                entity_type="document",
                entity_id=command.document_id,
                collection=command.collection,
                error_type=type(e).__name__,
                error_message=str(e),
                duration_ms=error_duration * 1000
            )
            raise

class CreateCollectionCommandHandler(CommandHandler[CreateCollectionCommand, None]):
    """Handler for CreateCollectionCommand with logging."""
    
    def __init__(self, vector_repository: VectorRepository):
        self.vector_repository = vector_repository
        self.logger = get_logger("document_processing.create_collection")
    
    @log_execution_time(operation_name="create_collection")
    @log_errors(reraise=True)
    def handle(self, command: CreateCollectionCommand) -> None:
        # Log operation start
        self.logger.log_business_event(
            event="collection_create_started",
            entity_type="collection",
            entity_id=command.name,
            vector_size=command.vector_size
        )
        
        # Create new collection in Qdrant
        self.vector_repository.create_collection(
            name=command.name,
            vector_size=command.vector_size
        )
        
        # Publish collection created event
        event_bus.publish(CollectionCreatedEvent(
            name=command.name,
            vector_size=command.vector_size
        ))
        
        # Log completion
        self.logger.log_business_event(
            event="collection_create_completed",
            entity_type="collection",
            entity_id=command.name,
            vector_size=command.vector_size
        )

class DeleteCollectionCommandHandler(CommandHandler[DeleteCollectionCommand, None]):
    """Handler for DeleteCollectionCommand with logging."""
    
    def __init__(self, vector_repository: VectorRepository):
        self.vector_repository = vector_repository
        self.logger = get_logger("document_processing.delete_collection")
    
    @log_execution_time(operation_name="delete_collection")
    @log_errors(reraise=True)
    def handle(self, command: DeleteCollectionCommand) -> None:
        # Log operation start
        self.logger.log_business_event(
            event="collection_delete_started",
            entity_type="collection",
            entity_id=command.name
        )
        
        # Delete collection from Qdrant
        self.vector_repository.delete_collection(command.name)
        
        # Publish collection deleted event
        event_bus.publish(CollectionDeletedEvent(name=command.name))
        
        # Log completion
        self.logger.log_business_event(
            event="collection_delete_completed",
            entity_type="collection",
            entity_id=command.name
        )

class UpdateDocumentLanguageCommandHandler(CommandHandler[UpdateDocumentLanguageCommand, None]):
    """Handler for UpdateDocumentLanguageCommand with logging."""
    
    def __init__(self, document_repository: DocumentRepository):
        self.document_repository = document_repository
        self.logger = get_logger("document_processing.update_language")
    
    @log_execution_time(operation_name="update_document_language")
    @log_errors(reraise=True)
    def handle(self, command: UpdateDocumentLanguageCommand) -> None:
        # Log operation start
        self.logger.log_business_event(
            event="document_language_update_started",
            entity_type="document",
            entity_id=command.document_id,
            new_language=command.language,
            collection=command.collection
        )
        
        # Get document
        document = self.document_repository.get_by_id(command.document_id)
        if not document:
            self.logger.error("Document not found for language update", context={
                "document_id": command.document_id,
                "collection": command.collection
            })
            raise ValueError(f"Document {command.document_id} not found")
        
        old_language = document.metadata.language
        
        # Update language in metadata
        document.metadata.language = command.language
        
        # Save document
        self.document_repository.save(document)
        
        # Log completion
        self.logger.log_business_event(
            event="document_language_update_completed",
            entity_type="document",
            entity_id=command.document_id,
            old_language=old_language,
            new_language=command.language,
            collection=command.collection
        )

class ReindexDocumentCommandHandler(CommandHandler[ReindexDocumentCommand, None]):
    """Handler for ReindexDocumentCommand with comprehensive logging."""
    
    def __init__(
        self,
        document_repository: DocumentRepository,
        vector_repository: VectorRepository,
        text_splitter: TextSplitter,
        embedding_generator: MultilingualEmbeddingGenerator,
        language_detector: LanguageDetector
    ):
        self.document_repository = document_repository
        self.vector_repository = vector_repository
        self.text_splitter = text_splitter
        self.embedding_generator = embedding_generator
        self.language_detector = language_detector
        self.logger = get_logger("document_processing.reindex")
    
    @log_execution_time(operation_name="reindex_document")
    @log_errors(reraise=True)
    def handle(self, command: ReindexDocumentCommand) -> None:
        """Handle ReindexDocumentCommand with comprehensive logging."""
        
        # Log operation start
        self.logger.log_business_event(
            event="document_reindex_started",
            entity_type="document",
            entity_id=command.document_id,
            collection=command.collection,
            new_chunk_size=command.chunk_size,
            new_chunk_overlap=command.chunk_overlap,
            new_language=command.language
        )
        
        start_time = time.time()
        
        try:
            # Get document
            document = self.document_repository.get_by_id(command.document_id)
            if not document:
                self.logger.error("Document not found for reindexing", context={
                    "document_id": command.document_id,
                    "collection": command.collection
                })
                raise ValueError(f"Document {command.document_id} not found")
            
            old_chunk_count = len(document.chunks)
            old_language = document.metadata.language
            
            self.logger.info("Document found for reindexing", context={
                "document_id": command.document_id,
                "old_chunk_count": old_chunk_count,
                "old_language": old_language,
                "content_length": len(document.content)
            })
            
            # Delete old vectors
            vector_delete_start = time.time()
            for chunk in document.chunks:
                self.vector_repository.delete_vector(
                    collection=command.collection,
                    id=chunk.id
                )
            vector_delete_duration = time.time() - vector_delete_start
            
            self.logger.info("Old vectors deleted", context={
                "document_id": command.document_id,
                "vectors_deleted": old_chunk_count,
                "delete_duration_ms": vector_delete_duration * 1000
            })
            
            # Update language if specified
            if command.language:
                document.metadata.language = command.language
                self.logger.info("Document language updated", context={
                    "document_id": command.document_id,
                    "old_language": old_language,
                    "new_language": command.language
                })
            
            # Determine chunk parameters
            chunk_size = command.chunk_size or 1000
            chunk_overlap = command.chunk_overlap or 200
            
            # Re-split document
            split_start = time.time()
            chunks = self.text_splitter.split_text(
                text=document.content,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap
            )
            split_duration = time.time() - split_start
            
            self.logger.info("Document re-split completed", context={
                "document_id": command.document_id,
                "new_chunk_count": len(chunks),
                "old_chunk_count": old_chunk_count,
                "split_duration_ms": split_duration * 1000,
                "chunk_size": chunk_size,
                "chunk_overlap": chunk_overlap
            })
            
            # Clear existing chunks
            document.chunks = []
            
            # Add new chunks with progress tracking
            chunk_processing_start = time.time()
            for i, chunk_text in enumerate(chunks):
                chunk_id = f"{document.id}_{i}"
                
                # Determine chunk language
                if document.metadata.language == "auto":
                    chunk_language, _ = self.language_detector.detect(chunk_text)
                else:
                    chunk_language = document.metadata.language
                    
                document.add_chunk(
                    chunk_id=chunk_id, 
                    chunk_content=chunk_text,
                    language=chunk_language
                )
            
            chunk_processing_duration = time.time() - chunk_processing_start
            self.logger.info("New chunks created", context={
                "document_id": command.document_id,
                "chunks_created": len(document.chunks),
                "processing_duration_ms": chunk_processing_duration * 1000
            })
            
            # Save document
            save_start = time.time()
            self.document_repository.save(document)
            save_duration = time.time() - save_start
            
            self.logger.info("Document saved with new chunks", context={
                "document_id": command.document_id,
                "save_duration_ms": save_duration * 1000
            })
            
            # Generate embeddings for each chunk with progress tracking
            embedding_start = time.time()
            chunk_ids = []
            embedding_progress = ProgressTracker(
                total=len(document.chunks),
                operation_name=f"reindex_embeddings_{command.document_id}",
                logger_name="document_processing.reindex_embeddings"
            )
            
            for chunk_idx, chunk in enumerate(document.chunks):
                chunk_embed_start = time.time()
                embedding = self.embedding_generator.generate(chunk.content)
                chunk_embed_duration = time.time() - chunk_embed_start
                
                chunk_ids.append(chunk.id)
                
                # Save embedding to vector storage
                self.vector_repository.add_vector(
                    collection=command.collection,
                    id=chunk.id,
                    vector=embedding,
                    metadata={
                        "document_id": document.id,
                        "chunk_index": chunk.index,
                        "content": chunk.content,
                        "language": chunk.language,
                        **document.metadata.to_dict()
                    }
                )
                
                # Update progress
                embedding_progress.update(current_item=f"chunk_{chunk_idx}")
                
                self.logger.debug("Chunk re-embedded", context={
                    "document_id": command.document_id,
                    "chunk_id": chunk.id,
                    "chunk_index": chunk_idx,
                    "embedding_duration_ms": chunk_embed_duration * 1000
                })
            
            embedding_duration = time.time() - embedding_start
            embedding_progress.complete(
                embeddings_generated=len(chunk_ids),
                avg_embedding_time_ms=(embedding_duration / len(chunk_ids)) * 1000 if chunk_ids else 0
            )
            
            # Publish events
            event_bus.publish(ChunksGeneratedEvent(
                document_id=document.id,
                chunk_count=len(document.chunks)
            ))
            
            event_bus.publish(EmbeddingsGeneratedEvent(
                document_id=document.id,
                chunk_ids=chunk_ids,
                collection=command.collection
            ))
            
            event_bus.publish(DocumentIndexedEvent(
                document_id=document.id,
                collection=command.collection,
                chunk_count=len(document.chunks),
                language=document.metadata.language
            ))
            
            # Log successful completion
            total_duration = time.time() - start_time
            self.logger.log_business_event(
                event="document_reindex_completed",
                entity_type="document",
                entity_id=command.document_id,
                collection=command.collection,
                old_chunk_count=old_chunk_count,
                new_chunk_count=len(document.chunks),
                old_language=old_language,
                new_language=document.metadata.language,
                total_duration_ms=total_duration * 1000
            )
            
            self.logger.log_performance(
                operation="reindex_document",
                duration=total_duration,
                old_chunks=old_chunk_count,
                new_chunks=len(document.chunks),
                embeddings_regenerated=len(chunk_ids),
                content_length=len(document.content)
            )
            
        except Exception as e:
            error_duration = time.time() - start_time
            self.logger.log_business_event(
                event="document_reindex_failed",
                entity_type="document",
                entity_id=command.document_id,
                collection=command.collection,
                error_type=type(e).__name__,
                error_message=str(e),
                duration_ms=error_duration * 1000
            )
            raise
