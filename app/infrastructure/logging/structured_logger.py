"""
Structured logging implementation for RAG system.
"""
import logging
import json
import sys
from datetime import datetime
from typing import Dict, Any, Optional, Union
from contextvars import ContextVar
from app.infrastructure.logging.correlation import get_correlation_id

# Context variable for additional logging context
_logging_context: ContextVar[Dict[str, Any]] = ContextVar('logging_context', default={})

class StructuredFormatter(logging.Formatter):
    """Custom formatter for structured logging."""
    
    def __init__(self, include_correlation_id: bool = True):
        super().__init__()
        self.include_correlation_id = include_correlation_id
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as structured JSON."""
        # Base log entry
        log_entry = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        # Add correlation ID if available
        if self.include_correlation_id:
            correlation_id = get_correlation_id()
            if correlation_id:
                log_entry['correlation_id'] = correlation_id
        
        # Add context variables
        context = _logging_context.get({})
        if context:
            log_entry['context'] = context
        
        # Add exception information if present
        if record.exc_info:
            log_entry['exception'] = {
                'type': record.exc_info[0].__name__ if record.exc_info[0] else None,
                'message': str(record.exc_info[1]) if record.exc_info[1] else None,
                'traceback': self.formatException(record.exc_info)
            }
        
        # Add extra fields
        extra_fields = {}
        for key, value in record.__dict__.items():
            if key not in ['name', 'msg', 'args', 'levelname', 'levelno', 'pathname', 
                          'filename', 'module', 'lineno', 'funcName', 'created', 
                          'msecs', 'relativeCreated', 'thread', 'threadName', 
                          'processName', 'process', 'getMessage', 'exc_info', 'exc_text', 'stack_info']:
                extra_fields[key] = value
        
        if extra_fields:
            log_entry['extra'] = extra_fields
        
        return json.dumps(log_entry, default=str, ensure_ascii=False)

class StructuredLogger:
    """Enhanced logger with structured logging capabilities."""
    
    def __init__(self, name: str, logger: Optional[logging.Logger] = None):
        self.name = name
        self.logger = logger or logging.getLogger(name)
    
    def _log_with_context(self, level: int, message: str, 
                         context: Optional[Dict[str, Any]] = None, 
                         **kwargs):
        """Log message with additional context."""
        # Temporarily set context
        if context:
            token = _logging_context.set(context)
        
        try:
            # Create extra fields for the log record
            extra = kwargs
            if 'extra' in kwargs:
                extra.update(kwargs['extra'])
                del kwargs['extra']
            
            self.logger.log(level, message, extra=extra, **kwargs)
        finally:
            if context:
                _logging_context.reset(token)
    
    def debug(self, message: str, context: Optional[Dict[str, Any]] = None, **kwargs):
        """Log debug message."""
        self._log_with_context(logging.DEBUG, message, context, **kwargs)
    
    def info(self, message: str, context: Optional[Dict[str, Any]] = None, **kwargs):
        """Log info message."""
        self._log_with_context(logging.INFO, message, context, **kwargs)
    
    def warning(self, message: str, context: Optional[Dict[str, Any]] = None, **kwargs):
        """Log warning message."""
        self._log_with_context(logging.WARNING, message, context, **kwargs)
    
    def error(self, message: str, context: Optional[Dict[str, Any]] = None, 
              exc_info: bool = False, **kwargs):
        """Log error message."""
        self._log_with_context(logging.ERROR, message, context, exc_info=exc_info, **kwargs)
    
    def critical(self, message: str, context: Optional[Dict[str, Any]] = None, 
                 exc_info: bool = False, **kwargs):
        """Log critical message."""
        self._log_with_context(logging.CRITICAL, message, context, exc_info=exc_info, **kwargs)
    
    def log_operation_start(self, operation: str, **params):
        """Log the start of an operation."""
        context = {
            'operation': operation,
            'operation_status': 'started',
            'parameters': params
        }
        self.info(f"Starting operation: {operation}", context=context)
    
    def log_operation_success(self, operation: str, duration: Optional[float] = None, **results):
        """Log successful completion of an operation."""
        context = {
            'operation': operation,
            'operation_status': 'completed',
            'results': results
        }
        if duration is not None:
            context['duration_ms'] = duration * 1000
        
        self.info(f"Operation completed successfully: {operation}", context=context)
    
    def log_operation_error(self, operation: str, error: Exception, 
                           duration: Optional[float] = None, **context_data):
        """Log operation failure."""
        context = {
            'operation': operation,
            'operation_status': 'failed',
            'error_type': type(error).__name__,
            'error_message': str(error),
            **context_data
        }
        if duration is not None:
            context['duration_ms'] = duration * 1000
        
        self.error(f"Operation failed: {operation}", context=context, exc_info=True)
    
    def log_performance(self, operation: str, duration: float, **metrics):
        """Log performance metrics."""
        context = {
            'operation': operation,
            'performance': {
                'duration_ms': duration * 1000,
                **metrics
            }
        }
        self.info(f"Performance metrics for: {operation}", context=context)
    
    def log_business_event(self, event: str, entity_type: str, entity_id: str, **data):
        """Log business events for audit and monitoring."""
        context = {
            'event_type': 'business_event',
            'event': event,
            'entity_type': entity_type,
            'entity_id': entity_id,
            'data': data
        }
        self.info(f"Business event: {event}", context=context)
    
    def log_user_action(self, action: str, user_id: Optional[str] = None, **data):
        """Log user actions for audit trail."""
        context = {
            'event_type': 'user_action',
            'action': action,
            'data': data
        }
        if user_id:
            context['user_id'] = user_id
        
        self.info(f"User action: {action}", context=context)
    
    def log_system_metrics(self, component: str, metrics: Dict[str, Union[int, float, str]]):
        """Log system metrics."""
        context = {
            'event_type': 'system_metrics',
            'component': component,
            'metrics': metrics
        }
        self.info(f"System metrics for: {component}", context=context)

def get_logger(name: str) -> StructuredLogger:
    """Get a structured logger instance."""
    return StructuredLogger(name)

def setup_structured_logging(
    level: str = "INFO",
    format_type: str = "structured",
    log_file: Optional[str] = None,
    include_correlation_id: bool = True
) -> logging.Logger:
    """Setup structured logging configuration."""
    
    # Convert level string to logging level
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    
    # Create root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    if format_type == "structured":
        formatter = StructuredFormatter(include_correlation_id=include_correlation_id)
    else:
        # Fallback to standard formatting
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # File handler if specified
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(numeric_level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    
    # Return root logger
    return root_logger
