"""
Comprehensive logging infrastructure for RAG document processing.
Provides structured logging with business events, performance metrics, and progress tracking.
"""
import logging
import time
import json
import functools
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime
from dataclasses import dataclass, asdict
import threading
from contextlib import contextmanager


class StructuredLogger:
    """Enhanced logger with structured logging capabilities for RAG operations."""
    
    def __init__(self, name: str, base_logger: logging.Logger):
        self.name = name
        self.logger = base_logger
        self._context = {}
    
    def set_context(self, **context):
        """Set persistent context for all log messages."""
        self._context.update(context)
    
    def clear_context(self):
        """Clear persistent context."""
        self._context.clear()
    
    def _format_message(self, message: str, context: Dict[str, Any] = None, 
                       event_type: str = None) -> str:
        """Format message with structured context."""
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "logger": self.name,
            "message": message
        }
        
        if event_type:
            log_data["event_type"] = event_type
        
        # Add persistent context
        if self._context:
            log_data["persistent_context"] = self._context
        
        # Add call-specific context
        if context:
            log_data["context"] = context
        
        return json.dumps(log_data, default=str, separators=(',', ':'))
    
    def debug(self, message: str, context: Dict[str, Any] = None, **kwargs):
        """Log debug message with structured context."""
        formatted_msg = self._format_message(message, context, "debug")
        self.logger.debug(formatted_msg, **kwargs)
    
    def info(self, message: str, context: Dict[str, Any] = None, **kwargs):
        """Log info message with structured context."""
        formatted_msg = self._format_message(message, context, "info")
        self.logger.info(formatted_msg, **kwargs)
    
    def warning(self, message: str, context: Dict[str, Any] = None, **kwargs):
        """Log warning message with structured context."""
        formatted_msg = self._format_message(message, context, "warning")
        self.logger.warning(formatted_msg, **kwargs)
    
    def error(self, message: str, context: Dict[str, Any] = None, **kwargs):
        """Log error message with structured context."""
        formatted_msg = self._format_message(message, context, "error")
        self.logger.error(formatted_msg, **kwargs)
    
    def critical(self, message: str, context: Dict[str, Any] = None, **kwargs):
        """Log critical message with structured context."""
        formatted_msg = self._format_message(message, context, "critical")
        self.logger.critical(formatted_msg, **kwargs)
    
    def log_business_event(self, event: str, entity_type: str = None, 
                          entity_id: str = None, **kwargs):
        """Log business events with standardized structure."""
        business_context = {
            "event": event,
            "entity_type": entity_type,
            "entity_id": entity_id,
            **kwargs
        }
        
        message = f"Business Event: {event}"
        if entity_type and entity_id:
            message += f" for {entity_type}:{entity_id}"
        
        formatted_msg = self._format_message(message, business_context, "business_event")
        self.logger.info(formatted_msg)
    
    def log_performance(self, operation: str, duration: float = None, **metrics):
        """Log performance metrics with standardized structure."""
        perf_context = {
            "operation": operation,
            "duration_seconds": duration,
            "metrics": metrics
        }
        
        message = f"Performance: {operation}"
        if duration:
            message += f" completed in {duration:.3f}s"
        
        formatted_msg = self._format_message(message, perf_context, "performance")
        self.logger.info(formatted_msg)


class ProgressTracker:
    """Tracks progress of long-running operations with detailed logging."""
    
    def __init__(self, total: int, operation_name: str, logger_name: str = None):
        self.total = total
        self.operation_name = operation_name
        self.current = 0
        self.start_time = time.time()
        self.last_log_time = self.start_time
        self.logger = get_logger(logger_name or f"progress.{operation_name}")
        
        # Configuration
        self.log_interval_seconds = 5.0  # Log progress every 5 seconds
        self.log_every_n_items = max(1, total // 20)  # Log every 5% of items
        
        # Start logging
        self.logger.log_business_event(
            event="progress_tracking_started",
            entity_type="operation",
            entity_id=operation_name,
            total_items=total
        )
    
    def update(self, current_item: str = None, increment: int = 1):
        """Update progress and log if necessary."""
        self.current += increment
        current_time = time.time()
        
        # Calculate progress metrics
        elapsed_time = current_time - self.start_time
        progress_percent = (self.current / self.total) * 100 if self.total > 0 else 0
        items_per_second = self.current / elapsed_time if elapsed_time > 0 else 0
        
        # Estimate remaining time
        if items_per_second > 0 and self.current < self.total:
            remaining_items = self.total - self.current
            eta_seconds = remaining_items / items_per_second
        else:
            eta_seconds = 0
        
        # Log progress based on conditions
        should_log = (
            current_time - self.last_log_time >= self.log_interval_seconds or
            self.current % self.log_every_n_items == 0 or
            self.current >= self.total
        )
        
        if should_log:
            self.logger.log_performance(
                operation=f"{self.operation_name}_progress",
                duration=elapsed_time,
                current_item=current_item,
                progress_current=self.current,
                progress_total=self.total,
                progress_percent=progress_percent,
                items_per_second=items_per_second,
                eta_seconds=eta_seconds
            )
            self.last_log_time = current_time
    
    def complete(self, **final_metrics):
        """Mark operation as complete and log final metrics."""
        total_duration = time.time() - self.start_time
        items_per_second = self.current / total_duration if total_duration > 0 else 0
        
        self.logger.log_business_event(
            event="progress_tracking_completed",
            entity_type="operation",
            entity_id=self.operation_name,
            items_processed=self.current,
            total_items=self.total,
            duration_seconds=total_duration,
            items_per_second=items_per_second,
            **final_metrics
        )


@dataclass
class BatchItem:
    """Represents an item in a batch operation."""
    id: str
    status: str = "pending"  # pending, processing, completed, failed
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    error: Optional[str] = None
    metrics: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metrics is None:
            self.metrics = {}


class BatchProgressLogger:
    """Specialized logger for batch processing operations."""
    
    def __init__(self, batch_name: str, logger_name: str = None):
        self.batch_name = batch_name
        self.logger = get_logger(logger_name or f"batch.{batch_name}")
        self.start_time = time.time()
        self.batches: Dict[str, BatchItem] = {}
        self.completed_count = 0
        self.failed_count = 0
        self._lock = threading.Lock()
        
        # Log batch operation start
        self.logger.log_business_event(
            event="batch_operation_started",
            entity_type="batch",
            entity_id=batch_name,
            start_time=self.start_time
        )
    
    def log_batch_start(self, batch_id: str, batch_size: int = 1, **context):
        """Log the start of a batch item."""
        with self._lock:
            self.batches[batch_id] = BatchItem(
                id=batch_id,
                status="processing",
                start_time=time.time(),
                metrics={"batch_size": batch_size, **context}
            )
        
        self.logger.debug("Batch item started", context={
            "batch_id": batch_id,
            "batch_size": batch_size,
            **context
        })
    
    def log_batch_complete(self, batch_id: str, items_processed: int = 0, **metrics):
        """Log successful completion of a batch item."""
        with self._lock:
            if batch_id in self.batches:
                batch_item = self.batches[batch_id]
                batch_item.status = "completed"
                batch_item.end_time = time.time()
                batch_item.metrics.update({
                    "items_processed": items_processed,
                    "duration_seconds": batch_item.end_time - batch_item.start_time,
                    **metrics
                })
                self.completed_count += 1
        
        self.logger.info("Batch item completed", context={
            "batch_id": batch_id,
            "items_processed": items_processed,
            "duration_ms": (batch_item.end_time - batch_item.start_time) * 1000,
            **metrics
        })
    
    def log_batch_error(self, batch_id: str, error: Exception, **context):
        """Log failure of a batch item."""
        with self._lock:
            if batch_id in self.batches:
                batch_item = self.batches[batch_id]
                batch_item.status = "failed"
                batch_item.end_time = time.time()
                batch_item.error = str(error)
                batch_item.metrics.update(context)
                self.failed_count += 1
        
        self.logger.error("Batch item failed", context={
            "batch_id": batch_id,
            "error_type": type(error).__name__,
            "error_message": str(error),
            "duration_ms": (batch_item.end_time - batch_item.start_time) * 1000,
            **context
        }, exc_info=True)
    
    def log_operation_summary(self) -> Dict[str, Any]:
        """Log summary of the entire batch operation."""
        end_time = time.time()
        total_duration = end_time - self.start_time
        total_batches = len(self.batches)
        
        # Calculate detailed metrics
        completed_batches = [b for b in self.batches.values() if b.status == "completed"]
        failed_batches = [b for b in self.batches.values() if b.status == "failed"]
        
        # Performance metrics
        avg_batch_duration = 0
        total_items_processed = 0
        
        if completed_batches:
            durations = [(b.end_time - b.start_time) for b in completed_batches]
            avg_batch_duration = sum(durations) / len(durations)
            total_items_processed = sum(b.metrics.get("items_processed", 0) for b in completed_batches)
        
        success_rate = (len(completed_batches) / total_batches) * 100 if total_batches > 0 else 0
        batches_per_second = total_batches / total_duration if total_duration > 0 else 0
        items_per_second = total_items_processed / total_duration if total_duration > 0 else 0
        
        summary = {
            "total_batches": total_batches,
            "completed_batches": len(completed_batches),
            "failed_batches": len(failed_batches),
            "success_rate_percent": success_rate,
            "total_duration_seconds": total_duration,
            "avg_batch_duration_seconds": avg_batch_duration,
            "batches_per_second": batches_per_second,
            "total_items_processed": total_items_processed,
            "items_per_second": items_per_second
        }
        
        self.logger.log_business_event(
            event="batch_operation_completed",
            entity_type="batch",
            entity_id=self.batch_name,
            **summary
        )
        
        return summary


def get_logger(name: str) -> StructuredLogger:
    """Get or create a structured logger for the given name."""
    base_logger = logging.getLogger(name)
    return StructuredLogger(name, base_logger)


def log_execution_time(operation_name: str = None, include_args: bool = True):
    """Decorator to log execution time of functions."""
    def decorator(func: Callable) -> Callable:
        op_name = operation_name or func.__name__
        logger = get_logger(f"timing.{func.__module__}.{func.__name__}")
        
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            
            # Prepare context for logging
            context = {"operation": op_name}
            if include_args and args:
                # Include class name if method
                if hasattr(args[0], '__class__'):
                    context["class_name"] = args[0].__class__.__name__
            
            logger.debug(f"Starting {op_name}", context=context)
            
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                
                logger.log_performance(
                    operation=op_name,
                    duration=duration,
                    status="success"
                )
                
                return result
                
            except Exception as e:
                duration = time.time() - start_time
                
                logger.log_performance(
                    operation=op_name,
                    duration=duration,
                    status="failed",
                    error_type=type(e).__name__,
                    error_message=str(e)
                )
                raise
        
        return wrapper
    return decorator


def log_errors(reraise: bool = True, log_level: str = "error"):
    """Decorator to log errors with full context."""
    def decorator(func: Callable) -> Callable:
        logger = get_logger(f"errors.{func.__module__}.{func.__name__}")
        
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                # Prepare error context
                error_context = {
                    "function": func.__name__,
                    "module": func.__module__,
                    "error_type": type(e).__name__,
                    "error_message": str(e)
                }
                
                # Add class name if method
                if args and hasattr(args[0], '__class__'):
                    error_context["class_name"] = args[0].__class__.__name__
                
                # Add function arguments (carefully)
                if kwargs:
                    # Only include safe arguments
                    safe_kwargs = {}
                    for k, v in kwargs.items():
                        if isinstance(v, (str, int, float, bool, type(None))):
                            safe_kwargs[k] = v
                        else:
                            safe_kwargs[k] = f"<{type(v).__name__}>"
                    if safe_kwargs:
                        error_context["function_kwargs"] = safe_kwargs
                
                # Log the error
                log_method = getattr(logger, log_level, logger.error)
                log_method(
                    f"Error in {func.__name__}: {str(e)}",
                    context=error_context,
                    exc_info=True
                )
                
                if reraise:
                    raise
                
                return None
        
        return wrapper
    return decorator


@contextmanager
def operation_context(operation_name: str, logger_name: str = None, **context):
    """Context manager for logging operation start/end with cleanup."""
    logger = get_logger(logger_name or f"operations.{operation_name}")
    start_time = time.time()
    
    logger.info(f"Operation started: {operation_name}", context=context)
    
    try:
        yield logger
        
        duration = time.time() - start_time
        logger.log_performance(
            operation=operation_name,
            duration=duration,
            status="completed",
            **context
        )
        
    except Exception as e:
        duration = time.time() - start_time
        logger.error(
            f"Operation failed: {operation_name}",
            context={
                "error_type": type(e).__name__,
                "error_message": str(e),
                "duration_seconds": duration,
                **context
            },
            exc_info=True
        )
        raise


class MetricsCollector:
    """Collects and aggregates performance metrics."""
    
    def __init__(self):
        self.metrics: Dict[str, List[float]] = {}
        self.counters: Dict[str, int] = {}
        self._lock = threading.Lock()
    
    def record_duration(self, operation: str, duration: float):
        """Record duration for an operation."""
        with self._lock:
            if operation not in self.metrics:
                self.metrics[operation] = []
            self.metrics[operation].append(duration)
    
    def increment_counter(self, counter_name: str, value: int = 1):
        """Increment a counter."""
        with self._lock:
            self.counters[counter_name] = self.counters.get(counter_name, 0) + value
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary of all collected metrics."""
        with self._lock:
            summary = {"counters": self.counters.copy()}
            
            duration_stats = {}
            for operation, durations in self.metrics.items():
                if durations:
                    duration_stats[operation] = {
                        "count": len(durations),
                        "total": sum(durations),
                        "average": sum(durations) / len(durations),
                        "min": min(durations),
                        "max": max(durations)
                    }
            
            summary["duration_stats"] = duration_stats
            return summary
    
    def reset(self):
        """Reset all metrics."""
        with self._lock:
            self.metrics.clear()
            self.counters.clear()


# Global metrics collector instance
metrics_collector = MetricsCollector()


def configure_rag_logging():
    """Configure logging specifically for RAG operations."""
    # Get root logger configuration
    from app.config.config_loader import get_config
    config = get_config()
    logging_config = config.get("logging", {})
    
    # Add RAG-specific formatters
    rag_formatter = logging.Formatter(
        fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Configure specific loggers for RAG operations
    rag_loggers = [
        "document_processing",
        "vector_operations", 
        "embeddings",
        "batch_processing",
        "performance",
        "business_events"
    ]
    
    for logger_name in rag_loggers:
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.INFO)
        
        # Add file handler if configured
        if "file" in logging_config:
            log_file = logging_config["file"]
            if log_file.endswith('.log'):
                # Create specific log file for this logger
                specific_log_file = log_file.replace('.log', f'_{logger_name}.log')
            else:
                specific_log_file = f"{log_file}_{logger_name}.log"
            
            file_handler = logging.FileHandler(specific_log_file)
            file_handler.setFormatter(rag_formatter)
            logger.addHandler(file_handler)
    
    # Configure metrics collection
    metrics_logger = get_logger("metrics.collection")
    
    def log_metrics_summary():
        """Log periodic metrics summary."""
        summary = metrics_collector.get_summary()
        if summary["counters"] or summary["duration_stats"]:
            metrics_logger.info("Metrics Summary", context=summary)
    
    # Set up periodic metrics logging (this would typically be done with a scheduler)
    return log_metrics_summary


# Export main functions and classes
__all__ = [
    "get_logger",
    "log_execution_time",
    "log_errors", 
    "ProgressTracker",
    "BatchProgressLogger",
    "StructuredLogger",
    "operation_context",
    "MetricsCollector",
    "metrics_collector",
    "configure_rag_logging"
]
