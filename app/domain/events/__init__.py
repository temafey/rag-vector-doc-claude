"""
Domain events for RAG system.
"""
from app.domain.events.document_events import (
    DocumentIndexedEvent,
    ChunksGeneratedEvent,
    EmbeddingsGeneratedEvent,
    DocumentDeletedEvent,
    CollectionCreatedEvent,
    CollectionDeletedEvent
)

__all__ = [
    'DocumentIndexedEvent',
    'ChunksGeneratedEvent',
    'EmbeddingsGeneratedEvent',
    'DocumentDeletedEvent',
    'CollectionCreatedEvent',
    'CollectionDeletedEvent'
]
