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

from typing import List, Dict, Any
import os
import uuid
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
    
    def handle(self, command: AddDocumentCommand) -> AddDocumentResult:
        # Determine document language if not specified
        document_language = command.language or "auto"
        if document_language == "auto":
            document_language, _ = self.language_detector.detect(command.content)
        
        # Create document metadata with language info
        metadata = DocumentMetadata(
            source="api",
            collection=command.collection,
            language=document_language,
            **command.metadata
        )
        
        # Create document
        document = Document(
            id=command.id,
            content=command.content,
            metadata=metadata
        )
        
        # Split document into chunks
        chunks = self.text_splitter.split_text(
            text=command.content,
            chunk_size=command.chunk_size,
            chunk_overlap=command.chunk_overlap
        )
        
        # Add chunks to document and generate embeddings
        for i, chunk_text in enumerate(chunks):
            chunk_id = f"{command.id}_{i}"
            
            # For large documents, language of each chunk might differ
            if self.config.get("languages", {}).get("detect_chunk_language", False):
                chunk_language, _ = self.language_detector.detect(chunk_text)
            else:
                chunk_language = document_language
                
            document.add_chunk(
                chunk_id=chunk_id, 
                chunk_content=chunk_text,
                language=chunk_language
            )
        
        # Save document
        self.document_repository.save(document)
        
        # Publish chunks generated event
        event_bus.publish(ChunksGeneratedEvent(
            document_id=document.id,
            chunk_count=len(document.chunks)
        ))
        
        # Generate embeddings for each chunk
        chunk_ids = []
        for chunk in document.chunks:
            embedding = self.embedding_generator.generate(chunk.content)
            chunk_ids.append(chunk.id)
            
            # Save embedding to vector storage (Qdrant)
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
        
        return AddDocumentResult(
            document_id=document.id,
            chunk_count=len(document.chunks)
        )

class AddFilesCommandHandler(CommandHandler[AddFilesCommand, AddFilesResult]):
    """Handler for AddFilesCommand."""
    
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
    
    def handle(self, command: AddFilesCommand) -> AddFilesResult:
        total_documents = 0
        total_chunks = 0
        
        # Process each file
        for file_path in command.files:
            # Get appropriate parser for file
            try:
                parser = self.parser_factory.get_parser(file_path)
            except ValueError as e:
                # Log error and skip file
                print(f"Error: {str(e)}")
                continue
            
            # Parse file into list of documents
            parsed_documents = parser.parse(file_path)
            
            # Process each document
            for parsed_doc in parsed_documents:
                doc_id = str(uuid.uuid4())
                
                # Determine metadata
                base_filename = os.path.basename(file_path)
                metadata = {
                    "source_file": base_filename,
                    "file_type": os.path.splitext(base_filename)[1][1:],  # File type without dot
                    **command.metadata
                }
                
                # If parsed document has metadata, add it
                if "metadata" in parsed_doc:
                    metadata.update(parsed_doc["metadata"])
                
                # Create command to add document
                add_doc_command = AddDocumentCommand(
                    id=doc_id,
                    content=parsed_doc["content"],
                    metadata=metadata,
                    collection=command.collection,
                    chunk_size=command.chunk_size,
                    chunk_overlap=command.chunk_overlap,
                    language=command.language
                )
                
                # Execute command through same handler
                from app.infrastructure.command_bus import command_bus
                result = command_bus.dispatch(add_doc_command)
                
                total_documents += 1
                total_chunks += result.chunk_count
        
        return AddFilesResult(
            total_documents=total_documents,
            total_chunks=total_chunks
        )

class DeleteDocumentCommandHandler(CommandHandler[DeleteDocumentCommand, None]):
    """Handler for DeleteDocumentCommand."""
    
    def __init__(
        self,
        document_repository: DocumentRepository,
        vector_repository: VectorRepository
    ):
        self.document_repository = document_repository
        self.vector_repository = vector_repository
    
    def handle(self, command: DeleteDocumentCommand) -> None:
        # Get document
        document = self.document_repository.get_by_id(command.document_id)
        if not document:
            return  # Document not found
        
        # Delete vectors from Qdrant
        for chunk in document.chunks:
            self.vector_repository.delete_vector(
                collection=command.collection,
                id=chunk.id
            )
        
        # Delete document from repository
        self.document_repository.delete(command.document_id)
        
        # Publish document deleted event
        event_bus.publish(DocumentDeletedEvent(
            document_id=command.document_id,
            collection=command.collection
        ))

class CreateCollectionCommandHandler(CommandHandler[CreateCollectionCommand, None]):
    """Handler for CreateCollectionCommand."""
    
    def __init__(self, vector_repository: VectorRepository):
        self.vector_repository = vector_repository
    
    def handle(self, command: CreateCollectionCommand) -> None:
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

class DeleteCollectionCommandHandler(CommandHandler[DeleteCollectionCommand, None]):
    """Handler for DeleteCollectionCommand."""
    
    def __init__(self, vector_repository: VectorRepository):
        self.vector_repository = vector_repository
    
    def handle(self, command: DeleteCollectionCommand) -> None:
        # Delete collection from Qdrant
        self.vector_repository.delete_collection(command.name)
        
        # Publish collection deleted event
        event_bus.publish(CollectionDeletedEvent(
            name=command.name
        ))

class UpdateDocumentLanguageCommandHandler(CommandHandler[UpdateDocumentLanguageCommand, None]):
    """Handler for UpdateDocumentLanguageCommand."""
    
    def __init__(
        self,
        document_repository: DocumentRepository
    ):
        self.document_repository = document_repository
    
    def handle(self, command: UpdateDocumentLanguageCommand) -> None:
        # Get document
        document = self.document_repository.get_by_id(command.document_id)
        if not document:
            raise ValueError(f"Document {command.document_id} not found")
        
        # Update language in metadata
        document.metadata.language = command.language
        
        # Save document
        self.document_repository.save(document)
        
        # Reindex might be needed, but that's a separate command

class ReindexDocumentCommandHandler(CommandHandler[ReindexDocumentCommand, None]):
    """Handler for ReindexDocumentCommand."""
    
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
    
    def handle(self, command: ReindexDocumentCommand) -> None:
        # Get document
        document = self.document_repository.get_by_id(command.document_id)
        if not document:
            raise ValueError(f"Document {command.document_id} not found")
        
        # Delete old vectors
        for chunk in document.chunks:
            self.vector_repository.delete_vector(
                collection=command.collection,
                id=chunk.id
            )
        
        # Update language if specified
        if command.language:
            document.metadata.language = command.language
        
        # Determine chunk parameters
        chunk_size = command.chunk_size or 1000
        chunk_overlap = command.chunk_overlap or 200
        
        # Re-split document
        chunks = self.text_splitter.split_text(
            text=document.content,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )
        
        # Clear existing chunks
        document.chunks = []
        
        # Add new chunks
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
        
        # Save document
        self.document_repository.save(document)
        
        # Generate embeddings for each chunk
        chunk_ids = []
        for chunk in document.chunks:
            embedding = self.embedding_generator.generate(chunk.content)
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
