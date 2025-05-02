"""
Event Bus implementation for event-driven architecture.
"""
from typing import Dict, List, Type, Callable, Any, Generic, TypeVar
from pydantic import BaseModel

# Type for event
E = TypeVar('E', bound=BaseModel)

class EventSubscriber(Generic[E]):
    """Base class for event subscribers."""
    
    def __init__(self):
        pass
    
    def handle(self, event: E) -> None:
        """Handle event."""
        raise NotImplementedError("Subclasses must implement handle method")

class EventBus:
    """Event bus for publishing and subscribing to events."""
    
    def __init__(self):
        self._subscribers: Dict[Type[BaseModel], List[EventSubscriber]] = {}
    
    def subscribe(self, event_type: Type[E], subscriber: EventSubscriber[E]):
        """Subscribe to specific event type."""
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        
        self._subscribers[event_type].append(subscriber)
    
    def publish(self, event: E) -> None:
        """Publish event to all subscribers."""
        # Get list of subscribers for this event type
        subscribers = self._subscribers.get(type(event), [])
        
        # Notify all subscribers
        for subscriber in subscribers:
            subscriber.handle(event)

# Create event bus instance
event_bus = EventBus()
