"""
Query Bus implementation for CQRS pattern.
"""
from typing import Dict, Type, Any, Generic, TypeVar
from pydantic import BaseModel

# Type for query
Q = TypeVar('Q', bound=BaseModel)
# Type for query result
R = TypeVar('R')

class QueryHandler(Generic[Q, R]):
    """Base class for query handlers."""
    
    def __init__(self):
        pass
    
    def handle(self, query: Q) -> R:
        """Handle query and return result."""
        raise NotImplementedError("Subclasses must implement handle method")

class QueryBus:
    """Query bus for routing queries to handlers."""
    
    def __init__(self):
        self._handlers: Dict[Type[BaseModel], QueryHandler] = {}
    
    def register(self, query_type: Type[Q], handler: QueryHandler[Q, Any]):
        """Register handler for specific query type."""
        self._handlers[query_type] = handler
    
    def dispatch(self, query: Q) -> Any:
        """Dispatch query to the appropriate handler."""
        handler = self._handlers.get(type(query))
        if not handler:
            raise ValueError(f"No handler registered for query type {type(query).__name__}")
        
        return handler.handle(query)

# Create query bus instance
query_bus = QueryBus()
