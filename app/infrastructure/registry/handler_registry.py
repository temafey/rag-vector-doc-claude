"""
Handler registry for automatic discovery and registration.
"""
import inspect
import importlib
from typing import Dict, Type, Any, Tuple, List
from pathlib import Path
from app.infrastructure.command_bus import CommandHandler, CommandBus
from app.infrastructure.query_bus import QueryHandler, QueryBus
from app.infrastructure.event_bus import EventBus


class HandlerRegistry:
    """Registry for automatic handler discovery and registration."""
    
    def __init__(self, command_bus: CommandBus, query_bus: QueryBus, event_bus: EventBus):
        self.command_bus = command_bus
        self.query_bus = query_bus
        self.event_bus = event_bus
        self.discovered_handlers: Dict[str, Any] = {}
        
    def discover_handlers(self, base_path: str = "app.application.handlers") -> Dict[str, List[Type]]:
        """
        Discover all handler classes in the handlers directory.
        
        Returns:
            Dictionary mapping handler types to lists of handler classes
        """
        handlers = {
            'command_handlers': [],
            'query_handlers': [],
            'event_handlers': []
        }
        
        # Import handler modules
        handler_modules = [
            f"{base_path}.document_handlers.command_handlers",
            f"{base_path}.document_handlers.query_handlers", 
            f"{base_path}.agent_handlers.command_handlers",
            f"{base_path}.agent_handlers.query_handlers"
        ]
        
        for module_name in handler_modules:
            try:
                module = importlib.import_module(module_name)
                
                # Get all classes from the module
                for name, obj in inspect.getmembers(module, inspect.isclass):
                    if name.endswith('Handler') and obj.__module__ == module_name:
                        # Determine handler type based on inheritance
                        if self._is_command_handler(obj):
                            handlers['command_handlers'].append(obj)
                        elif self._is_query_handler(obj):
                            handlers['query_handlers'].append(obj)
                        elif self._is_event_handler(obj):
                            handlers['event_handlers'].append(obj)
                            
            except ImportError as e:
                print(f"Warning: Could not import {module_name}: {e}")
                
        return handlers
    
    def _is_command_handler(self, handler_class: Type) -> bool:
        """Check if a class is a command handler."""
        # Check if it inherits from CommandHandler or has handle method with command parameter
        return (hasattr(handler_class, '__orig_bases__') and 
                any('CommandHandler' in str(base) for base in getattr(handler_class, '__orig_bases__', [])))
    
    def _is_query_handler(self, handler_class: Type) -> bool:
        """Check if a class is a query handler."""
        # Check if it inherits from QueryHandler or has handle method with query parameter
        return (hasattr(handler_class, '__orig_bases__') and 
                any('QueryHandler' in str(base) for base in getattr(handler_class, '__orig_bases__', [])))
    
    def _is_event_handler(self, handler_class: Type) -> bool:
        """Check if a class is an event handler."""
        # For now, we don't have explicit event handlers, but this is for future use
        return False
    
    def _extract_generic_types(self, handler_class: Type) -> Tuple[Type, Type]:
        """
        Extract command/query and result types from generic handler class.
        
        Returns:
            Tuple of (request_type, response_type)
        """
        if hasattr(handler_class, '__orig_bases__'):
            for base in handler_class.__orig_bases__:
                if hasattr(base, '__args__') and len(base.__args__) >= 2:
                    return base.__args__[0], base.__args__[1]
        
        # Fallback: try to infer from method signatures
        if hasattr(handler_class, 'handle'):
            sig = inspect.signature(handler_class.handle)
            params = list(sig.parameters.values())
            if len(params) >= 2:  # self + request parameter
                request_type = params[1].annotation
                return_type = sig.return_annotation
                return request_type, return_type
                
        return None, None
    
    def auto_register_handlers(self, dependencies: Dict[str, Any]) -> None:
        """
        Automatically discover and register all handlers with their dependencies.
        
        Args:
            dependencies: Dictionary of available dependencies for dependency injection
        """
        handlers = self.discover_handlers()
        
        # Register command handlers
        for handler_class in handlers['command_handlers']:
            try:
                request_type, response_type = self._extract_generic_types(handler_class)
                if request_type:
                    handler_instance = self._create_handler_instance(handler_class, dependencies)
                    self.command_bus.register(request_type, handler_instance)
                    print(f"Registered command handler: {handler_class.__name__} for {request_type.__name__}")
            except Exception as e:
                print(f"Failed to register command handler {handler_class.__name__}: {e}")
        
        # Register query handlers
        for handler_class in handlers['query_handlers']:
            try:
                request_type, response_type = self._extract_generic_types(handler_class)
                if request_type:
                    handler_instance = self._create_handler_instance(handler_class, dependencies)
                    self.query_bus.register(request_type, handler_instance)
                    print(f"Registered query handler: {handler_class.__name__} for {request_type.__name__}")
            except Exception as e:
                print(f"Failed to register query handler {handler_class.__name__}: {e}")
    
    def _create_handler_instance(self, handler_class: Type, dependencies: Dict[str, Any]) -> Any:
        """
        Create handler instance with dependency injection.
        
        Args:
            handler_class: Handler class to instantiate
            dependencies: Available dependencies
            
        Returns:
            Handler instance
        """
        # Get constructor signature
        sig = inspect.signature(handler_class.__init__)
        
        # Prepare arguments for constructor
        kwargs = {}
        for param_name, param in sig.parameters.items():
            if param_name == 'self':
                continue
                
            # Try to find matching dependency
            param_type = param.annotation
            
            # Look for dependency by type annotation
            for dep_name, dep_instance in dependencies.items():
                if (param_type != inspect.Parameter.empty and 
                    isinstance(dep_instance, param_type)):
                    kwargs[param_name] = dep_instance
                    break
                # Also try exact name match
                elif param_name == dep_name:
                    kwargs[param_name] = dep_instance
                    break
            
            # If dependency not found and parameter has no default, raise error
            if param_name not in kwargs and param.default == inspect.Parameter.empty:
                raise ValueError(f"Cannot resolve dependency '{param_name}' for {handler_class.__name__}")
        
        return handler_class(**kwargs)
    
    def get_registered_handlers(self) -> Dict[str, List[str]]:
        """Get summary of registered handlers."""
        return {
            'command_handlers': list(self.command_bus._handlers.keys()),
            'query_handlers': list(self.query_bus._handlers.keys()),
            'total_handlers': len(self.command_bus._handlers) + len(self.query_bus._handlers)
        }


def create_handler_registry(command_bus: CommandBus, query_bus: QueryBus, event_bus: EventBus) -> HandlerRegistry:
    """Factory function to create handler registry."""
    return HandlerRegistry(command_bus, query_bus, event_bus)
