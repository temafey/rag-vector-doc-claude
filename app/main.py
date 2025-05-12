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

# Import document commands and queries
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

# Import agent commands and queries
from app.application.commands.agent_commands import (
    CreateAgentCommand,
    DeleteAgentCommand,
    ExecuteAgentActionCommand,
    ProcessAgentQueryCommand,
    CreatePlanCommand,
    ExecutePlanCommand,
    EvaluateResponseCommand,
    ImproveResponseCommand
)
from app.application.queries.agent_queries import (
    GetAgentByIdQuery,
    GetAgentByConversationIdQuery,
    ListAgentsQuery,
    GetAgentActionsQuery,
    GetPlanByIdQuery,
    ListPlansByAgentIdQuery,
    GetEvaluationByIdQuery,
    ListEvaluationsByAgentIdQuery,
    GetImprovementByIdQuery,
    GetImprovementByEvaluationIdQuery
)
from app.application.handlers.agent_handlers import (
    CreateAgentCommandHandler,
    DeleteAgentCommandHandler,
    ExecuteAgentActionCommandHandler,
    ProcessAgentQueryCommandHandler,
    CreatePlanCommandHandler,
    ExecutePlanCommandHandler,
    EvaluateResponseCommandHandler,
    ImproveResponseCommandHandler,
    GetAgentByIdQueryHandler,
    GetAgentByConversationIdQueryHandler,
    ListAgentsQueryHandler,
    GetAgentActionsQueryHandler,
    GetPlanByIdQueryHandler,
    ListPlansByAgentIdQueryHandler,
    GetEvaluationByIdQueryHandler,
    ListEvaluationsByAgentIdQueryHandler,
    GetImprovementByIdQueryHandler,
    GetImprovementByEvaluationIdQueryHandler,
    GetAvailableActionsQueryHandler
)

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
    
    # Initialize agent repositories
    logger.info("Initializing agent repositories")
    agent_repository = AgentRepository(storage_path=storage_path)
    plan_repository = PlanRepository(storage_path=storage_path)
    evaluation_repository = EvaluationRepository(storage_path=storage_path)
    
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
    
    # Initialize agent services
    logger.info("Initializing agent services")
    # Create action registry and register actions
    action_registry = ActionRegistry()
    
    # Create search action
    def search_action(agent, parameters):
        """Search action for agent."""
        query = parameters.get("query", "")
        collection = parameters.get("collection", "default")
        limit = parameters.get("limit", 5)
        
        # Create search query
        search_query = SearchQuery(
            query_text=query,
            collection=collection,
            limit=limit
        )
        
        # Execute query
        search_result = query_bus.dispatch(search_query)
        
        # Return sources
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
    
    # Create generate action
    def generate_action(agent, parameters):
        """Generate response action for agent."""
        query = parameters.get("query", "")
        context = parameters.get("context", [])
        language = parameters.get("language", "en")
        
        # Format context if not a list
        if not isinstance(context, list):
            context = [str(context)]
        
        # Extract content from context if it's a list of dicts
        if context and isinstance(context[0], dict):
            context = [item.get("content", "") for item in context]
        
        # Generate response
        response = response_generator.generate(
            query=query,
            context=context,
            language=language
        )
        
        return response
    
    # Register actions
    action_registry.register_action(
        "search",
        search_action,
        {"description": "Search for information in the vector database"}
    )
    action_registry.register_action(
        "generate",
        generate_action,
        {"description": "Generate a response based on provided context"}
    )
    
    # Create agent service
    agent_service = AgentService(action_registry=action_registry)
    
    # Create planning service
    planning_service = PlanningService(agent_service=agent_service)
    
    # Create evaluation service
    evaluation_service = EvaluationService()
    
    # Register evaluate action
    def evaluate_action(agent, parameters):
        """Evaluate response action for agent."""
        query = parameters.get("query", "")
        response = parameters.get("response", "")
        context = parameters.get("context", [])
        
        # Format context if not a list
        if not isinstance(context, list):
            context = [str(context)]
        
        # Extract content from context if it's a list of dicts
        if context and isinstance(context[0], dict):
            context = [item.get("content", "") for item in context]
        
        # Evaluate response
        evaluation = evaluation_service.evaluate_response(
            agent=agent,
            query=query,
            response=response,
            context=context
        )
        
        # Save evaluation
        evaluation_repository.save_evaluation(evaluation)
        
        # Determine if improvement is needed
        needs_improvement = evaluation.needs_improvement(
            evaluation_service.quality_thresholds,
            evaluation_service.overall_threshold
        )
        
        # Return evaluation result
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
    
    # Register improve action
    def improve_action(agent, parameters):
        """Improve response action for agent."""
        query = parameters.get("query", "")
        response = parameters.get("response", "")
        context = parameters.get("context", [])
        evaluation_result = parameters.get("evaluation", {})
        
        # If evaluation ID is provided, get evaluation
        evaluation_id = evaluation_result.get("evaluation_id")
        if evaluation_id:
            evaluation = evaluation_repository.get_evaluation_by_id(evaluation_id)
        else:
            # Create evaluation if not provided
            evaluation = evaluation_service.evaluate_response(
                agent=agent,
                query=query,
                response=response,
                context=context
            )
            evaluation_repository.save_evaluation(evaluation)
        
        # Improve response
        improvement = evaluation_service.improve_response(
            agent=agent,
            evaluation=evaluation
        )
        
        # Save improvement
        evaluation_repository.save_improvement(improvement)
        
        # Return improvement result
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
    
    # Register additional actions
    action_registry.register_action(
        "evaluate",
        evaluate_action,
        {"description": "Evaluate the quality of a response"}
    )
    action_registry.register_action(
        "improve",
        improve_action,
        {"description": "Improve a response based on evaluation"}
    )
    
    # Register command handlers
    logger.info("Registering document command handlers")
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
    
    # Register agent command handlers
    logger.info("Registering agent command handlers")
    command_bus.register(
        CreateAgentCommand,
        CreateAgentCommandHandler(
            agent_service=agent_service,
            agent_repository=agent_repository
        )
    )
    command_bus.register(
        DeleteAgentCommand,
        DeleteAgentCommandHandler(
            agent_repository=agent_repository
        )
    )
    command_bus.register(
        ExecuteAgentActionCommand,
        ExecuteAgentActionCommandHandler(
            agent_service=agent_service,
            agent_repository=agent_repository
        )
    )
    command_bus.register(
        ProcessAgentQueryCommand,
        ProcessAgentQueryCommandHandler(
            agent_service=agent_service,
            planning_service=planning_service,
            agent_repository=agent_repository
        )
    )
    command_bus.register(
        CreatePlanCommand,
        CreatePlanCommandHandler(
            planning_service=planning_service,
            agent_repository=agent_repository,
            plan_repository=plan_repository
        )
    )
    command_bus.register(
        ExecutePlanCommand,
        ExecutePlanCommandHandler(
            planning_service=planning_service,
            agent_repository=agent_repository,
            plan_repository=plan_repository
        )
    )
    command_bus.register(
        EvaluateResponseCommand,
        EvaluateResponseCommandHandler(
            evaluation_service=evaluation_service,
            agent_repository=agent_repository,
            evaluation_repository=evaluation_repository
        )
    )
    command_bus.register(
        ImproveResponseCommand,
        ImproveResponseCommandHandler(
            evaluation_service=evaluation_service,
            agent_repository=agent_repository,
            evaluation_repository=evaluation_repository
        )
    )
    
    # Register document query handlers
    logger.info("Registering document query handlers")
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
    
    # Register agent query handlers
    logger.info("Registering agent query handlers")
    query_bus.register(
        GetAgentByIdQuery,
        GetAgentByIdQueryHandler(
            agent_repository=agent_repository
        )
    )
    query_bus.register(
        GetAgentByConversationIdQuery,
        GetAgentByConversationIdQueryHandler(
            agent_repository=agent_repository
        )
    )
    query_bus.register(
        ListAgentsQuery,
        ListAgentsQueryHandler(
            agent_repository=agent_repository
        )
    )
    query_bus.register(
        GetAgentActionsQuery,
        GetAgentActionsQueryHandler(
            agent_repository=agent_repository
        )
    )
    query_bus.register(
        GetPlanByIdQuery,
        GetPlanByIdQueryHandler(
            plan_repository=plan_repository
        )
    )
    query_bus.register(
        ListPlansByAgentIdQuery,
        ListPlansByAgentIdQueryHandler(
            plan_repository=plan_repository
        )
    )
    query_bus.register(
        GetEvaluationByIdQuery,
        GetEvaluationByIdQueryHandler(
            evaluation_repository=evaluation_repository
        )
    )
    query_bus.register(
        ListEvaluationsByAgentIdQuery,
        ListEvaluationsByAgentIdQueryHandler(
            evaluation_repository=evaluation_repository
        )
    )
    query_bus.register(
        GetImprovementByIdQuery,
        GetImprovementByIdQueryHandler(
            evaluation_repository=evaluation_repository
        )
    )
    query_bus.register(
        GetImprovementByEvaluationIdQuery,
        GetImprovementByEvaluationIdQueryHandler(
            evaluation_repository=evaluation_repository
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
