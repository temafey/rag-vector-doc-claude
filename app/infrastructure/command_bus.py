"""
Command Bus implementation for CQRS pattern.
"""
from typing import Dict, Type, Any, Generic, TypeVar
from pydantic import BaseModel

# Type for command
C = TypeVar('C', bound=BaseModel)
# Type for command result
R = TypeVar('R')

class CommandHandler(Generic[C, R]):
    """Base class for command handlers."""
    
    def __init__(self):
        pass
    
    def handle(self, command: C) -> R:
        """Handle command and return result."""
        raise NotImplementedError("Subclasses must implement handle method")

class CommandBus:
    """Command bus for routing commands to handlers."""
    
    def __init__(self):
        self._handlers: Dict[Type[BaseModel], CommandHandler] = {}
    
    def register(self, command_type: Type[C], handler: CommandHandler[C, Any]):
        """Register handler for specific command type."""
        self._handlers[command_type] = handler
    
    def dispatch(self, command: C) -> Any:
        """Dispatch command to the appropriate handler."""
        handler = self._handlers.get(type(command))
        if not handler:
            raise ValueError(f"No handler registered for command type {type(command).__name__}")
        
        return handler.handle(command)

# Create command bus instance
command_bus = CommandBus()
