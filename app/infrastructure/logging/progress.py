"""
Progress tracking and logging for batch operations.
"""
import time
from typing import Callable, Optional, Any, Dict, List
from dataclasses import dataclass
from app.infrastructure.logging.structured_logger import get_logger

@dataclass
class ProgressInfo:
    """Information about operation progress."""
    current: int
    total: int
    percentage: float
    elapsed_time: float
    estimated_total_time: Optional[float] = None
    estimated_remaining_time: Optional[float] = None
    items_per_second: Optional[float] = None
    current_item: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging."""
        return {
            'current': self.current,
            'total': self.total,
            'percentage': round(self.percentage, 2),
            'elapsed_time_seconds': round(self.elapsed_time, 2),
            'estimated_total_time_seconds': round(self.estimated_total_time, 2) if self.estimated_total_time else None,
            'estimated_remaining_time_seconds': round(self.estimated_remaining_time, 2) if self.estimated_remaining_time else None,
            'items_per_second': round(self.items_per_second, 2) if self.items_per_second else None,
            'current_item': self.current_item
        }

class ProgressTracker:
    """Track progress of operations with detailed logging."""
    
    def __init__(self, 
                 total: int, 
                 operation_name: str,
                 logger_name: Optional[str] = None,
                 log_interval: int = 10,
                 log_percentage_interval: float = 10.0):
        """
        Initialize progress tracker.
        
        Args:
            total: Total number of items to process
            operation_name: Name of the operation being tracked
            logger_name: Custom logger name
            log_interval: Log every N items
            log_percentage_interval: Log every N percent progress
        """
        self.total = total
        self.operation_name = operation_name
        self.logger = get_logger(logger_name or __name__)
        self.log_interval = log_interval
        self.log_percentage_interval = log_percentage_interval
        
        self.current = 0
        self.start_time = time.time()
        self.last_log_time = self.start_time
        self.last_log_count = 0
        self.last_log_percentage = 0
        
        # Log start
        self.logger.log_operation_start(
            self.operation_name,
            total_items=self.total,
            log_interval=self.log_interval
        )
    
    def update(self, increment: int = 1, current_item: Optional[str] = None):
        """Update progress."""
        self.current += increment
        current_time = time.time()
        elapsed_time = current_time - self.start_time
        
        # Calculate progress info
        percentage = (self.current / self.total) * 100 if self.total > 0 else 0
        items_per_second = self.current / elapsed_time if elapsed_time > 0 else None
        estimated_total_time = (elapsed_time / self.current) * self.total if self.current > 0 else None
        estimated_remaining_time = estimated_total_time - elapsed_time if estimated_total_time else None
        
        progress_info = ProgressInfo(
            current=self.current,
            total=self.total,
            percentage=percentage,
            elapsed_time=elapsed_time,
            estimated_total_time=estimated_total_time,
            estimated_remaining_time=estimated_remaining_time,
            items_per_second=items_per_second,
            current_item=current_item
        )
        
        # Determine if we should log
        should_log = (
            (self.current - self.last_log_count) >= self.log_interval or
            (percentage - self.last_log_percentage) >= self.log_percentage_interval or
            self.current >= self.total
        )
        
        if should_log:
            self.logger.info(
                f"Progress update: {self.operation_name}",
                context={
                    'operation': self.operation_name,
                    'progress': progress_info.to_dict()
                }
            )
            
            self.last_log_time = current_time
            self.last_log_count = self.current
            self.last_log_percentage = percentage
        
        return progress_info
    
    def complete(self, **results):
        """Mark operation as complete."""
        elapsed_time = time.time() - self.start_time
        
        self.logger.log_operation_success(
            self.operation_name,
            duration=elapsed_time,
            total_items=self.total,
            items_processed=self.current,
            items_per_second=self.current / elapsed_time if elapsed_time > 0 else None,
            **results
        )
    
    def error(self, error: Exception, **context):
        """Mark operation as failed."""
        elapsed_time = time.time() - self.start_time
        
        self.logger.log_operation_error(
            self.operation_name,
            error,
            duration=elapsed_time,
            total_items=self.total,
            items_processed=self.current,
            **context
        )

def progress_callback(operation_name: str, 
                     total: int,
                     logger_name: Optional[str] = None) -> Callable[[int, int], None]:
    """
    Create a progress callback function for use with batch operations.
    
    Args:
        operation_name: Name of the operation
        total: Total number of items
        logger_name: Custom logger name
        
    Returns:
        Callback function that accepts (current, total) parameters
    """
    logger = get_logger(logger_name or __name__)
    start_time = time.time()
    last_log_time = start_time
    last_percentage = 0
    
    def callback(current: int, total_items: int = None):
        nonlocal last_log_time, last_percentage
        
        # Use provided total or fallback to initial total
        total_count = total_items or total
        
        current_time = time.time()
        elapsed_time = current_time - start_time
        percentage = (current / total_count) * 100 if total_count > 0 else 0
        
        # Log every 10% or every 30 seconds
        time_since_last_log = current_time - last_log_time
        percentage_change = percentage - last_percentage
        
        if percentage_change >= 10 or time_since_last_log >= 30 or current >= total_count:
            items_per_second = current / elapsed_time if elapsed_time > 0 else None
            estimated_total_time = (elapsed_time / current) * total_count if current > 0 else None
            estimated_remaining_time = estimated_total_time - elapsed_time if estimated_total_time else None
            
            logger.info(
                f"Batch progress: {operation_name}",
                context={
                    'operation': operation_name,
                    'progress': {
                        'current': current,
                        'total': total_count,
                        'percentage': round(percentage, 1),
                        'elapsed_time_seconds': round(elapsed_time, 1),
                        'estimated_remaining_time_seconds': round(estimated_remaining_time, 1) if estimated_remaining_time else None,
                        'items_per_second': round(items_per_second, 2) if items_per_second else None
                    }
                }
            )
            
            last_log_time = current_time
            last_percentage = percentage
    
    return callback

class BatchProgressLogger:
    """Logger for batch operations with detailed progress tracking."""
    
    def __init__(self, operation_name: str, logger_name: Optional[str] = None):
        self.operation_name = operation_name
        self.logger = get_logger(logger_name or __name__)
        self.batches: List[Dict[str, Any]] = []
        self.start_time = time.time()
    
    def log_batch_start(self, batch_id: str, batch_size: int, **context):
        """Log the start of a batch."""
        batch_info = {
            'batch_id': batch_id,
            'batch_size': batch_size,
            'start_time': time.time(),
            'status': 'started',
            **context
        }
        self.batches.append(batch_info)
        
        self.logger.info(
            f"Batch started: {self.operation_name}",
            context={
                'operation': self.operation_name,
                'batch': batch_info
            }
        )
    
    def log_batch_complete(self, batch_id: str, items_processed: int, **results):
        """Log batch completion."""
        # Find and update batch info
        batch_info = next((b for b in self.batches if b['batch_id'] == batch_id), None)
        if batch_info:
            batch_info['status'] = 'completed'
            batch_info['end_time'] = time.time()
            batch_info['duration'] = batch_info['end_time'] - batch_info['start_time']
            batch_info['items_processed'] = items_processed
            batch_info['results'] = results
            
            self.logger.info(
                f"Batch completed: {self.operation_name}",
                context={
                    'operation': self.operation_name,
                    'batch': batch_info
                }
            )
    
    def log_batch_error(self, batch_id: str, error: Exception, **context):
        """Log batch error."""
        # Find and update batch info
        batch_info = next((b for b in self.batches if b['batch_id'] == batch_id), None)
        if batch_info:
            batch_info['status'] = 'failed'
            batch_info['end_time'] = time.time()
            batch_info['duration'] = batch_info['end_time'] - batch_info['start_time']
            batch_info['error'] = str(error)
            batch_info['error_type'] = type(error).__name__
            
            self.logger.error(
                f"Batch failed: {self.operation_name}",
                context={
                    'operation': self.operation_name,
                    'batch': batch_info,
                    **context
                },
                exc_info=True
            )
    
    def log_operation_summary(self):
        """Log summary of the entire operation."""
        end_time = time.time()
        total_duration = end_time - self.start_time
        
        # Calculate statistics
        total_batches = len(self.batches)
        completed_batches = len([b for b in self.batches if b.get('status') == 'completed'])
        failed_batches = len([b for b in self.batches if b.get('status') == 'failed'])
        total_items = sum(b.get('items_processed', 0) for b in self.batches)
        
        summary = {
            'total_duration_seconds': round(total_duration, 2),
            'total_batches': total_batches,
            'completed_batches': completed_batches,
            'failed_batches': failed_batches,
            'total_items_processed': total_items,
            'items_per_second': round(total_items / total_duration, 2) if total_duration > 0 else None,
            'success_rate': round((completed_batches / total_batches) * 100, 1) if total_batches > 0 else None
        }
        
        self.logger.info(
            f"Operation summary: {self.operation_name}",
            context={
                'operation': self.operation_name,
                'summary': summary
            }
        )
        
        return summary
