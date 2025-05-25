"""
Registry infrastructure for RAG system.
"""
from app.infrastructure.registry.handler_registry import HandlerRegistry, create_handler_registry

__all__ = [
    'HandlerRegistry',
    'create_handler_registry'
]
