"""
Command and query handlers for agent operations.
"""
from app.application.handlers.agent_handlers.command_handlers import (
    CreateAgentCommandHandler,
    DeleteAgentCommandHandler,
    ExecuteAgentActionCommandHandler,
    ProcessAgentQueryCommandHandler,
    CreatePlanCommandHandler,
    ExecutePlanCommandHandler,
    EvaluateResponseCommandHandler,
    ImproveResponseCommandHandler
)
from app.application.handlers.agent_handlers.query_handlers import (
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
    # Command handlers
    'CreateAgentCommandHandler',
    'DeleteAgentCommandHandler',
    'ExecuteAgentActionCommandHandler',
    'ProcessAgentQueryCommandHandler',
    'CreatePlanCommandHandler',
    'ExecutePlanCommandHandler',
    'EvaluateResponseCommandHandler',
    'ImproveResponseCommandHandler',
    
    # Query handlers
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
