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
    CreateAgentCommand,
    DeleteAgentCommand,
    ExecuteAgentActionCommand,
    ProcessAgentQueryCommand,
    CreatePlanCommand,
    ExecutePlanCommand,
    EvaluateResponseCommand,
    ImproveResponseCommand
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
    'DeleteAgentCommand',
    'ExecuteAgentActionCommand',
    'ProcessAgentQueryCommand',
    'CreatePlanCommand',
    'ExecutePlanCommand',
    'EvaluateResponseCommand',
    'ImproveResponseCommand'
]
