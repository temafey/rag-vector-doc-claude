"""
Results for RAG system commands.
"""
from app.application.results.document_results import (
    AddDocumentResult,
    AddFilesResult
)
from app.application.results.agent_results import (
    CreateAgentResult,
    ExecuteAgentActionResult,
    ProcessAgentQueryResult,
    CreatePlanResult,
    ExecutePlanResult,
    EvaluateResponseResult,
    ImproveResponseResult
)

__all__ = [
    # Document results
    'AddDocumentResult',
    'AddFilesResult',
    
    # Agent results
    'CreateAgentResult',
    'ExecuteAgentActionResult',
    'ProcessAgentQueryResult',
    'CreatePlanResult',
    'ExecutePlanResult',
    'EvaluateResponseResult',
    'ImproveResponseResult'
]
