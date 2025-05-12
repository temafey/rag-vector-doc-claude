"""
Commands for RAG system.
"""
from app.application.commands.document_commands import (
    AddDocumentCommand,
    AddFilesCommand,
    DeleteDocumentCommand,
    CreateCollectionCommand,
    DeleteCollectionCommand,
    UpdateDocumentLanguageCommand,
    ReindexDocumentCommand
)
from app.application.commands.agent_commands import (
    CreateAgentCommand, CreateAgentResult,
    DeleteAgentCommand,
    ExecuteAgentActionCommand, ExecuteAgentActionResult,
    ProcessAgentQueryCommand, ProcessAgentQueryResult,
    CreatePlanCommand, CreatePlanResult,
    ExecutePlanCommand, ExecutePlanResult,
    EvaluateResponseCommand, EvaluateResponseResult,
    ImproveResponseCommand, ImproveResponseResult
)

__all__ = [
    # Document commands
    'AddDocumentCommand',
    'AddFilesCommand',
    'DeleteDocumentCommand',
    'CreateCollectionCommand',
    'DeleteCollectionCommand',
    'UpdateDocumentLanguageCommand',
    'ReindexDocumentCommand',
    
    # Agent commands
    'CreateAgentCommand',
    'CreateAgentResult',
    'DeleteAgentCommand',
    'ExecuteAgentActionCommand',
    'ExecuteAgentActionResult',
    'ProcessAgentQueryCommand',
    'ProcessAgentQueryResult',
    'CreatePlanCommand',
    'CreatePlanResult',
    'ExecutePlanCommand',
    'ExecutePlanResult',
    'EvaluateResponseCommand',
    'EvaluateResponseResult',
    'ImproveResponseCommand',
    'ImproveResponseResult'
]
