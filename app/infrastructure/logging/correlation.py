"""
Correlation ID implementation for request tracking.
"""
import uuid
from contextvars import ContextVar
from typing import Optional
from fastapi import Request, Response
from fastapi.middleware.base import BaseHTTPMiddleware

# Context variable to store correlation ID
_correlation_id: ContextVar[Optional[str]] = ContextVar('correlation_id', default=None)

class CorrelationId:
    """Utility class for correlation ID management."""
    
    @staticmethod
    def generate() -> str:
        """Generate a new correlation ID."""
        return str(uuid.uuid4())
    
    @staticmethod
    def get() -> Optional[str]:
        """Get current correlation ID."""
        return _correlation_id.get()
    
    @staticmethod
    def set(correlation_id: str) -> None:
        """Set correlation ID."""
        _correlation_id.set(correlation_id)
    
    @staticmethod
    def clear() -> None:
        """Clear correlation ID."""
        _correlation_id.set(None)

def get_correlation_id() -> Optional[str]:
    """Get current correlation ID from context."""
    return _correlation_id.get()

def set_correlation_id(correlation_id: str) -> None:
    """Set correlation ID in context."""
    _correlation_id.set(correlation_id)

class CorrelationMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware to handle correlation IDs."""
    
    def __init__(self, app, header_name: str = "X-Correlation-ID"):
        super().__init__(app)
        self.header_name = header_name
    
    async def dispatch(self, request: Request, call_next):
        """Process request and set correlation ID."""
        # Get correlation ID from header or generate new one
        correlation_id = request.headers.get(self.header_name)
        if not correlation_id:
            correlation_id = CorrelationId.generate()
        
        # Set correlation ID in context
        token = _correlation_id.set(correlation_id)
        
        try:
            # Process request
            response = await call_next(request)
            
            # Add correlation ID to response headers
            response.headers[self.header_name] = correlation_id
            
            return response
        finally:
            # Reset context
            _correlation_id.reset(token)

def correlation_middleware(app):
    """Add correlation middleware to FastAPI app."""
    app.add_middleware(CorrelationMiddleware)
    return app
