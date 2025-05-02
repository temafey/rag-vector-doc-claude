"""
Main entry point for RAG system.
"""
import os
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config.config_loader import get_config
from app.infrastructure.command_bus import command_bus
from app.infrastructure.query_bus import query_bus
from app.infrastructure.event_bus import event_bus
from app.infrastructure.repositories.document_repository import DocumentRepository
from app.infrastructure.repositories.vector_repository import VectorRepository
from app.domain.services.text_splitter import TextSplitter
from app.domain.services.embedding_generator import EmbeddingGenerator
from app.domain.services.multilingual_embedding_generator import MultilingualEmbeddingGenerator
from app.domain.services.response_generator import ResponseGenerator
from app.domain.services.language_detector import LanguageDetector
from app.domain.services.translation_service import TranslationService
from app.infrastructure.parsers.parser_factory import ParserFactory
from app.infrastructure.parsers.csv_parser import CsvParser
from app.infrastructure.parsers.json_parser import JsonParser
from app.infrastructure.parsers.txt_parser import TxtParser
from app.infrastructure.parsers.pdf_parser import PdfParser

from app.application.commands.document_commands import (
    AddDocumentCommand,
    AddFilesCommand,
    DeleteDocumentCommand,
    CreateCollectionCommand,
    DeleteCollectionCommand,
    UpdateDocumentLanguageCommand,
    ReindexDocumentCommand
)
from app.application.queries.document_queries import (
    SearchQuery,
    GetDocumentByIdQuery,
    ListCollectionsQuery,
    GetSimilarDocumentsQuery,
    GetDocumentsByFilterQuery
)
from app.application.handlers.document_handlers import (
    AddDocumentCommandHandler,
    AddFilesCommandHandler,
    DeleteDocumentCommandHandler,
    CreateCollectionCommandHandler,
    DeleteCollectionCommandHandler,
    UpdateDocumentLanguageCommandHandler,
    ReindexDocumentCommandHandler
)
from app.application.handlers.query_handlers import (
    SearchQueryHandler,
    GetDocumentByIdQueryHandler,
    ListCollectionsQueryHandler,
    GetSimilarDocumentsQueryHandler,
    GetDocumentsByFilterQueryHandler
)

from app.api.routes import router as api_router

# Configure logging
def setup_logging():
    """Configure logging based on settings."""
    config = get_config()
    logging_config = config.get("logging", {})
    
    level = getattr(logging, logging_config.get("level", "INFO"))
    log_format = logging_config.get("format", "%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    
    logging.basicConfig(
        level=level,
        format=log_format
    )
    
    # Configure file logging if specified
    if "file" in logging_config:
        file_handler = logging.FileHandler(logging_config["file"])
        file_handler.setFormatter(logging.Formatter(log_format))
        
        root_logger = logging.getLogger()
        root_logger.addHandler(file_handler)
    
    return logging.getLogger("rag-system")

# Create FastAPI application
def create_app():
    """Create and configure FastAPI application."""
    config = get_config()
    app_config = config.get("app", {})
    
    # Create FastAPI app
    app = FastAPI(
        title=app_config.get("name", "RAG API"),
        description=app_config.get("description", "API for RAG system"),
        version=app_config.get("version", "0.1.0"),
        debug=app_config.get("debug", False)
    )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Include API routes
    app.include_router(api_router)
    
    return app

# Initialize application
def init_app():
    """Initialize application components."""
    logger = setup_logging()
    logger.info("Initializing RAG system")
    
    # Get configuration
    config = get_config()
    
    # Get settings from configuration
    qdrant_host = config["qdrant"]["host"]
    qdrant_port = int(config["qdrant"]["port"])
    storage_path = config["storage"]["document_path"]
    
    # Create storage directory
    os.makedirs(storage_path, exist_ok=True)
    
    # Initialize repositories
    logger.info(f"Initializing document repository at {storage_path}")
    document_repository = DocumentRepository(storage_path=storage_path)
    
    logger.info(f"Connecting to Qdrant at {qdrant_host}:{qdrant_port}")
    vector_repository = VectorRepository(host=qdrant_host, port=qdrant_port)
    
    # Initialize domain services
    logger.info("Initializing domain services")
    text_splitter = TextSplitter()
    embedding_generator = EmbeddingGenerator()
    multilingual_embedding_generator = MultilingualEmbeddingGenerator()
    language_detector = LanguageDetector()
    translation_service = TranslationService()
    response_generator = ResponseGenerator()
    
    # Initialize parser factory
    logger.info("Initializing parser factory")
    parser_factory = ParserFactory()
    parser_factory.register_parser(CsvParser())
    parser_factory.register_parser(JsonParser())
    parser_factory.register_parser(TxtParser())
    parser_factory.register_parser(PdfParser())
    
    # Register command handlers
    logger.info("Registering command handlers")
    command_bus.register(
        AddDocumentCommand,
        AddDocumentCommandHandler(
            document_repository=document_repository,
            vector_repository=vector_repository,
            text_splitter=text_splitter,
            embedding_generator=multilingual_embedding_generator,
            language_detector=language_detector
        )
    )
    command_bus.register(
        AddFilesCommand,
        AddFilesCommandHandler(
            document_repository=document_repository,
            vector_repository=vector_repository,
            text_splitter=text_splitter,
            embedding_generator=multilingual_embedding_generator,
            language_detector=language_detector,
            parser_factory=parser_factory
        )
    )
    command_bus.register(
        DeleteDocumentCommand,
        DeleteDocumentCommandHandler(
            document_repository=document_repository,
            vector_repository=vector_repository
        )
    )
    command_bus.register(
        CreateCollectionCommand,
        CreateCollectionCommandHandler(
            vector_repository=vector_repository
        )
    )
    command_bus.register(
        DeleteCollectionCommand,
        DeleteCollectionCommandHandler(
            vector_repository=vector_repository
        )
    )
    command_bus.register(
        UpdateDocumentLanguageCommand,
        UpdateDocumentLanguageCommandHandler(
            document_repository=document_repository
        )
    )
    command_bus.register(
        ReindexDocumentCommand,
        ReindexDocumentCommandHandler(
            document_repository=document_repository,
            vector_repository=vector_repository,
            text_splitter=text_splitter,
            embedding_generator=multilingual_embedding_generator,
            language_detector=language_detector
        )
    )
    
    # Register query handlers
    logger.info("Registering query handlers")
    query_bus.register(
        SearchQuery,
        SearchQueryHandler(
            document_repository=document_repository,
            vector_repository=vector_repository,
            embedding_generator=multilingual_embedding_generator,
            response_generator=response_generator,
            language_detector=language_detector,
            translation_service=translation_service
        )
    )
    query_bus.register(
        GetDocumentByIdQuery,
        GetDocumentByIdQueryHandler(
            document_repository=document_repository
        )
    )
    query_bus.register(
        ListCollectionsQuery,
        ListCollectionsQueryHandler(
            vector_repository=vector_repository
        )
    )
    query_bus.register(
        GetSimilarDocumentsQuery,
        GetSimilarDocumentsQueryHandler(
            document_repository=document_repository,
            vector_repository=vector_repository,
            embedding_generator=multilingual_embedding_generator
        )
    )
    query_bus.register(
        GetDocumentsByFilterQuery,
        GetDocumentsByFilterQueryHandler(
            document_repository=document_repository,
            vector_repository=vector_repository
        )
    )
    
    logger.info("RAG system initialized")
    
    # Create FastAPI app
    app = create_app()
    return app

# Create app
app = init_app()

# For running from command line
if __name__ == "__main__":
    import uvicorn
    
    # Get configuration
    config = get_config()
    api_config = config.get("api", {})
    
    uvicorn.run(
        "app.main:app",
        host=api_config.get("host", "0.0.0.0"),
        port=api_config.get("port", 8000),
        reload=api_config.get("reload", False),
        workers=api_config.get("workers", 1)
    )
