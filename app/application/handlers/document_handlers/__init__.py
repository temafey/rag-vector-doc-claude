"""
Document handlers for RAG system.
"""
from app.application.handlers.document_handlers.command_handlers import (
    AddDocumentCommandHandler,
    AddFilesCommandHandler,
    DeleteDocumentCommandHandler,
    CreateCollectionCommandHandler,
    DeleteCollectionCommandHandler,
    UpdateDocumentLanguageCommandHandler,
    ReindexDocumentCommandHandler
)
from app.application.handlers.document_handlers.query_handlers import (
    SearchQueryHandler,
    GetDocumentByIdQueryHandler,
    ListCollectionsQueryHandler,
    GetSimilarDocumentsQueryHandler,
    GetDocumentsByFilterQueryHandler
)

__all__ = [
    # Command handlers
    'AddDocumentCommandHandler',
    'AddFilesCommandHandler',
    'DeleteDocumentCommandHandler',
    'CreateCollectionCommandHandler',
    'DeleteCollectionCommandHandler',
    'UpdateDocumentLanguageCommandHandler',
    'ReindexDocumentCommandHandler',
    
    # Query handlers
    'SearchQueryHandler',
    'GetDocumentByIdQueryHandler',
    'ListCollectionsQueryHandler',
    'GetSimilarDocumentsQueryHandler',
    'GetDocumentsByFilterQueryHandler'
]
