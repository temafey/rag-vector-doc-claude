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
from app.domain.events.agent_events import (
    AgentCreatedEvent,
    AgentActionStartedEvent,
    AgentActionCompletedEvent,
    AgentActionFailedEvent,
    PlanCreatedEvent,
    PlanStepCompletedEvent,
    PlanCompletedEvent,
    ResponseEvaluatedEvent,
    ResponseImprovedEvent
)

__all__ = [
    # Document events
    'DocumentIndexedEvent',
    'ChunksGeneratedEvent',
    'EmbeddingsGeneratedEvent',
    'DocumentDeletedEvent',
    'CollectionCreatedEvent',
    'CollectionDeletedEvent',
    
    # Agent events
    'AgentCreatedEvent',
    'AgentActionStartedEvent',
    'AgentActionCompletedEvent',
    'AgentActionFailedEvent',
    'PlanCreatedEvent',
    'PlanStepCompletedEvent',
    'PlanCompletedEvent',
    'ResponseEvaluatedEvent',
    'ResponseImprovedEvent'
]
