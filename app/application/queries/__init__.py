"""
Queries for RAG system.
"""
from app.application.queries.document_queries import (
    SearchQuery,
    GetDocumentByIdQuery,
    ListCollectionsQuery,
    GetSimilarDocumentsQuery,
    GetDocumentsByFilterQuery
)
from app.application.queries.agent_queries import (
    GetAgentByIdQuery, AgentResult,
    GetAgentByConversationIdQuery,
    ListAgentsQuery, AgentListResult,
    GetAgentActionsQuery, AgentActionsResult,
    GetPlanByIdQuery, PlanResult,
    ListPlansByAgentIdQuery, PlanListResult,
    GetEvaluationByIdQuery, EvaluationResult,
    ListEvaluationsByAgentIdQuery, EvaluationListResult,
    GetImprovementByIdQuery, ImprovementResult,
    GetImprovementByEvaluationIdQuery,
    AvailableActionsResult
)

__all__ = [
    # Document queries
    'SearchQuery',
    'GetDocumentByIdQuery',
    'ListCollectionsQuery',
    'GetSimilarDocumentsQuery',
    'GetDocumentsByFilterQuery',
    
    # Agent queries
    'GetAgentByIdQuery',
    'AgentResult',
    'GetAgentByConversationIdQuery',
    'ListAgentsQuery',
    'AgentListResult',
    'GetAgentActionsQuery',
    'AgentActionsResult',
    'GetPlanByIdQuery',
    'PlanResult',
    'ListPlansByAgentIdQuery',
    'PlanListResult',
    'GetEvaluationByIdQuery',
    'EvaluationResult',
    'ListEvaluationsByAgentIdQuery',
    'EvaluationListResult',
    'GetImprovementByIdQuery',
    'ImprovementResult',
    'GetImprovementByEvaluationIdQuery',
    'AvailableActionsResult'
]
