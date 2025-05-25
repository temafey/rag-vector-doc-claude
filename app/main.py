"""
Main entry point for RAG system with auto-registration.
"""
import os
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config.config_loader import get_config
from app.infrastructure.command_bus import command_bus
from app.infrastructure.query_bus import query_bus
from app.infrastructure.event_bus import event_bus
from app.infrastructure.registry import create_handler_registry
from app.infrastructure.repositories.document_repository import DocumentRepository
from app.infrastructure.repositories.vector_repository import VectorRepository
from app.infrastructure.repositories.agent import (
    AgentRepository,
    PlanRepository,
    EvaluationRepository
)
from app.domain.services.text_splitter import TextSplitter
from app.domain.services.embedding_generator import EmbeddingGenerator
from app.domain.services.multilingual_embedding_generator import MultilingualEmbeddingGenerator
from app.domain.services.response_generator import ResponseGenerator
from app.domain.services.language_detector import LanguageDetector
from app.domain.services.translation_service import TranslationService
from app.domain.services.agent import (
    AgentService, 
    ActionRegistry,
    PlanningService,
    EvaluationService
)
from app.infrastructure.parsers.parser_factory import ParserFactory
from app.infrastructure.parsers.csv_parser import CsvParser
from app.infrastructure.parsers.json_parser import JsonParser
from app.infrastructure.parsers.txt_parser import TxtParser
from app.infrastructure.parsers.pdf_parser import PdfParser
from app.application.queries.document_queries import SearchQuery
from app.api import document_router, agent_router

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
    
    # Initialize RAG-specific logging
    from app.infrastructure.logging import configure_rag_logging
    configure_rag_logging()
    
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
    app.include_router(document_router)
    app.include_router(agent_router)
    
    return app

def setup_dependencies():
    """Set up all dependencies for dependency injection."""
    config = get_config()
    
    # Get settings from configuration
    qdrant_host = config["qdrant"]["host"]
    qdrant_port = int(config["qdrant"]["port"])
    storage_path = config["storage"]["document_path"]
    
    # Create storage directory
    os.makedirs(storage_path, exist_ok=True)
    
    # Initialize repositories
    document_repository = DocumentRepository(storage_path=storage_path)
    vector_repository = VectorRepository(host=qdrant_host, port=qdrant_port)
    agent_repository = AgentRepository(storage_path=storage_path)
    plan_repository = PlanRepository(storage_path=storage_path)
    evaluation_repository = EvaluationRepository(storage_path=storage_path)
    
    # Initialize domain services
    text_splitter = TextSplitter()
    embedding_generator = EmbeddingGenerator()
    multilingual_embedding_generator = MultilingualEmbeddingGenerator()
    language_detector = LanguageDetector()
    translation_service = TranslationService()
    response_generator = ResponseGenerator()
    
    # Initialize parser factory
    parser_factory = ParserFactory()
    parser_factory.register_parser(CsvParser())
    parser_factory.register_parser(JsonParser())
    parser_factory.register_parser(TxtParser())
    parser_factory.register_parser(PdfParser())
    
    # Initialize agent services
    action_registry = ActionRegistry()
    
    # Create agent actions
    def search_action(agent, parameters):
        """Search action for agent."""
        query = parameters.get("query", "")
        collection = parameters.get("collection", "default")
        limit = parameters.get("limit", 5)
        
        search_query = SearchQuery(
            query_text=query,
            collection=collection,
            limit=limit
        )
        
        search_result = query_bus.dispatch(search_query)
        
        return [
            {
                "id": source.id,
                "title": source.title,
                "content": source.content,
                "metadata": source.metadata,
                "score": source.score
            }
            for source in search_result.sources
        ]
    
    def generate_action(agent, parameters):
        """Generate response action for agent."""
        query = parameters.get("query", "")
        context = parameters.get("context", [])
        language = parameters.get("language", "en")
        
        if not isinstance(context, list):
            context = [str(context)]
        
        if context and isinstance(context[0], dict):
            context = [item.get("content", "") for item in context]
        
        return response_generator.generate(
            query=query,
            context=context,
            language=language
        )
    
    def evaluate_action(agent, parameters):
        """Evaluate response action for agent."""
        query = parameters.get("query", "")
        response = parameters.get("response", "")
        context = parameters.get("context", [])
        
        if not isinstance(context, list):
            context = [str(context)]
        
        if context and isinstance(context[0], dict):
            context = [item.get("content", "") for item in context]
        
        evaluation = evaluation_service.evaluate_response(
            agent=agent,
            query=query,
            response=response,
            context=context
        )
        
        evaluation_repository.save_evaluation(evaluation)
        
        needs_improvement = evaluation.needs_improvement(
            evaluation_service.quality_thresholds,
            evaluation_service.overall_threshold
        )
        
        return {
            "evaluation_id": evaluation.id,
            "overall_score": evaluation.overall_score,
            "criterion_scores": {
                criterion: {
                    "score": score.score,
                    "reason": score.reason
                }
                for criterion, score in evaluation.scores.items()
            },
            "needs_improvement": needs_improvement
        }
    
    def improve_action(agent, parameters):
        """Improve response action for agent."""
        query = parameters.get("query", "")
        response = parameters.get("response", "")
        context = parameters.get("context", [])
        evaluation_result = parameters.get("evaluation", {})
        
        evaluation_id = evaluation_result.get("evaluation_id")
        if evaluation_id:
            evaluation = evaluation_repository.get_evaluation_by_id(evaluation_id)
        else:
            evaluation = evaluation_service.evaluate_response(
                agent=agent,
                query=query,
                response=response,
                context=context
            )
            evaluation_repository.save_evaluation(evaluation)
        
        improvement = evaluation_service.improve_response(
            agent=agent,
            evaluation=evaluation
        )
        
        evaluation_repository.save_improvement(improvement)
        
        return {
            "improvement_id": improvement.id,
            "original_response": improvement.original_response,
            "improved_response": improvement.improved_response,
            "suggestions": [
                {
                    "criterion": suggestion.criterion,
                    "suggestion": suggestion.suggestion,
                    "priority": suggestion.priority
                }
                for suggestion in improvement.suggestions
            ]
        }
    
    # Register actions
    action_registry.register_action("search", search_action, {"description": "Search for information in the vector database"})
    action_registry.register_action("generate", generate_action, {"description": "Generate a response based on provided context"})
    action_registry.register_action("evaluate", evaluate_action, {"description": "Evaluate the quality of a response"})
    action_registry.register_action("improve", improve_action, {"description": "Improve a response based on evaluation"})
    
    # Create agent services
    agent_service = AgentService(action_registry=action_registry)
    planning_service = PlanningService(agent_service=agent_service)
    evaluation_service = EvaluationService()
    
    # Return dependencies dictionary
    return {
        # Repositories
        'document_repository': document_repository,
        'vector_repository': vector_repository,
        'agent_repository': agent_repository,
        'plan_repository': plan_repository,
        'evaluation_repository': evaluation_repository,
        
        # Domain Services
        'text_splitter': text_splitter,
        'embedding_generator': embedding_generator,
        'multilingual_embedding_generator': multilingual_embedding_generator,
        'language_detector': language_detector,
        'translation_service': translation_service,
        'response_generator': response_generator,
        
        # Agent Services
        'agent_service': agent_service,
        'planning_service': planning_service,
        'evaluation_service': evaluation_service,
        'action_registry': action_registry,
        
        # Infrastructure
        'parser_factory': parser_factory
    }

# Initialize application
def init_app():
    """Initialize application components with auto-registration."""
    logger = setup_logging()
    logger.info("Initializing RAG system with auto-registration")
    
    # Setup all dependencies
    logger.info("Setting up dependencies")
    dependencies = setup_dependencies()
    
    # Create handler registry
    logger.info("Creating handler registry")
    handler_registry = create_handler_registry(command_bus, query_bus, event_bus)
    
    # Auto-register all handlers
    logger.info("Auto-registering handlers")
    handler_registry.auto_register_handlers(dependencies)
    
    # Log registration summary
    summary = handler_registry.get_registered_handlers()
    logger.info(f"Handler registration complete: {summary['total_handlers']} handlers registered")
    logger.info(f"Command handlers: {len(summary['command_handlers'])}")
    logger.info(f"Query handlers: {len(summary['query_handlers'])}")
    
    logger.info("RAG system initialized successfully")
    
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
