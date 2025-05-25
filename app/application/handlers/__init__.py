"""
Command and query handlers for RAG system.
"""
from app.application.handlers.document_handlers import (
    AddDocumentCommandHandler,
    AddFilesCommandHandler,
    DeleteDocumentCommandHandler,
    CreateCollectionCommandHandler,
    DeleteCollectionCommandHandler,
    UpdateDocumentLanguageCommandHandler,
    ReindexDocumentCommandHandler,
    SearchQueryHandler,
    GetDocumentByIdQueryHandler,
    ListCollectionsQueryHandler,
    GetSimilarDocumentsQueryHandler,
    GetDocumentsByFilterQueryHandler
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

__all__ = [
    # Document handlers
    'AddDocumentCommandHandler',
    'AddFilesCommandHandler',
    'DeleteDocumentCommandHandler',
    'CreateCollectionCommandHandler',
    'DeleteCollectionCommandHandler',
    'UpdateDocumentLanguageCommandHandler',
    'ReindexDocumentCommandHandler',
    'SearchQueryHandler',
    'GetDocumentByIdQueryHandler',
    'ListCollectionsQueryHandler',
    'GetSimilarDocumentsQueryHandler',
    'GetDocumentsByFilterQueryHandler',
    
    # Agent handlers
    'CreateAgentCommandHandler',
    'DeleteAgentCommandHandler',
    'ExecuteAgentActionCommandHandler',
    'ProcessAgentQueryCommandHandler',
    'CreatePlanCommandHandler',
    'ExecutePlanCommandHandler',
    'EvaluateResponseCommandHandler',
    'ImproveResponseCommandHandler',
    'GetAgentByIdQueryHandler',
    'GetAgentByConversationIdQueryHandler',
    'ListAgentsQueryHandler',
    'GetAgentActionsQueryHandler',
    'GetPlanByIdQueryHandler',
    'ListPlansByAgentIdQueryHandler',
    'GetEvaluationByIdQueryHandler',
    'ListEvaluationsByAgentIdQueryHandler',
    'GetImprovementByIdQueryHandler',
    'GetImprovementByEvaluationIdQueryHandler',
    'GetAvailableActionsQueryHandler'
]
