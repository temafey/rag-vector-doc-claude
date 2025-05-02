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

__all__ = [
    'AddDocumentCommand',
    'AddFilesCommand',
    'DeleteDocumentCommand',
    'CreateCollectionCommand',
    'DeleteCollectionCommand',
    'UpdateDocumentLanguageCommand',
    'ReindexDocumentCommand'
]
