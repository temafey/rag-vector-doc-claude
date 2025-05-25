"""
Logging decorators for method instrumentation.
"""
import time
import functools
from typing import Callable, Any, Optional, Dict
from app.infrastructure.logging.structured_logger import get_logger

def log_execution_time(
    operation_name: Optional[str] = None,
    logger_name: Optional[str] = None,
    include_args: bool = False,
    include_result: bool = False,
    log_level: str = 'INFO'
):
    """
    Decorator to log execution time of functions/methods.
    
    Args:
        operation_name: Custom name for the operation (defaults to function name)
        logger_name: Custom logger name (defaults to module name)
        include_args: Whether to log function arguments
        include_result: Whether to log function result
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Setup logger
            logger = get_logger(logger_name or func.__module__)
            op_name = operation_name or f"{func.__name__}"
            
            # Prepare context
            context = {
                'function': func.__name__,
                'module': func.__module__
            }
            
            if include_args:
                context['arguments'] = {
                    'args': [str(arg) for arg in args],
                    'kwargs': {k: str(v) for k, v in kwargs.items()}
                }
            
            # Start timing
            start_time = time.time()
            
            try:
                # Log operation start
                logger.log_operation_start(op_name, **context)
                
                # Execute function
                result = func(*args, **kwargs)
                
                # Calculate duration
                duration = time.time() - start_time
                
                # Prepare result context
                result_context = {}
                if include_result and result is not None:
                    result_context['result'] = str(result)[:500]  # Limit result size
                
                # Log success
                logger.log_operation_success(op_name, duration=duration, **result_context)
                logger.log_performance(op_name, duration=duration)
                
                return result
                
            except Exception as e:
                # Calculate duration even for errors
                duration = time.time() - start_time
                
                # Log error
                logger.log_operation_error(op_name, e, duration=duration)
                raise
        
        return wrapper
    return decorator

def log_method_entry_exit(
    logger_name: Optional[str] = None,
    include_args: bool = False,
    include_result: bool = False
):
    """
    Decorator to log method entry and exit.
    
    Args:
        logger_name: Custom logger name
        include_args: Whether to log method arguments
        include_result: Whether to log method result
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Setup logger
            logger = get_logger(logger_name or func.__module__)
            
            # Prepare context
            context = {
                'method': func.__name__,
                'class': args[0].__class__.__name__ if args and hasattr(args[0], '__class__') else None
            }
            
            if include_args:
                context['arguments'] = {
                    'args': [str(arg) for arg in args[1:]],  # Skip self
                    'kwargs': {k: str(v) for k, v in kwargs.items()}
                }
            
            # Log entry
            logger.debug(f"Entering method: {func.__name__}", context=context)
            
            try:
                # Execute method
                result = func(*args, **kwargs)
                
                # Prepare exit context
                exit_context = context.copy()
                if include_result and result is not None:
                    exit_context['result'] = str(result)[:200]  # Limit result size
                
                # Log exit
                logger.debug(f"Exiting method: {func.__name__}", context=exit_context)
                
                return result
                
            except Exception as e:
                # Log exception
                error_context = context.copy()
                error_context['error'] = str(e)
                logger.error(f"Exception in method: {func.__name__}", context=error_context, exc_info=True)
                raise
        
        return wrapper
    return decorator

def log_errors(
    logger_name: Optional[str] = None,
    reraise: bool = True,
    default_return: Any = None
):
    """
    Decorator to log exceptions.
    
    Args:
        logger_name: Custom logger name
        reraise: Whether to reraise the exception
        default_return: Default value to return if not reraising
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Setup logger
            logger = get_logger(logger_name or func.__module__)
            
            try:
                return func(*args, **kwargs)
            except Exception as e:
                # Log error with context
                context = {
                    'function': func.__name__,
                    'module': func.__module__,
                    'error_type': type(e).__name__,
                    'error_message': str(e)
                }
                
                logger.error(f"Error in function: {func.__name__}", context=context, exc_info=True)
                
                if reraise:
                    raise
                else:
                    return default_return
        
        return wrapper
    return decorator

def log_async_execution_time(
    operation_name: Optional[str] = None,
    logger_name: Optional[str] = None,
    include_args: bool = False,
    include_result: bool = False
):
    """
    Async version of log_execution_time decorator.
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Setup logger
            logger = get_logger(logger_name or func.__module__)
            op_name = operation_name or f"{func.__name__}"
            
            # Prepare context
            context = {
                'function': func.__name__,
                'module': func.__module__,
                'async': True
            }
            
            if include_args:
                context['arguments'] = {
                    'args': [str(arg) for arg in args],
                    'kwargs': {k: str(v) for k, v in kwargs.items()}
                }
            
            # Start timing
            start_time = time.time()
            
            try:
                # Log operation start
                logger.log_operation_start(op_name, **context)
                
                # Execute async function
                result = await func(*args, **kwargs)
                
                # Calculate duration
                duration = time.time() - start_time
                
                # Prepare result context
                result_context = {}
                if include_result and result is not None:
                    result_context['result'] = str(result)[:500]
                
                # Log success
                logger.log_operation_success(op_name, duration=duration, **result_context)
                logger.log_performance(op_name, duration=duration)
                
                return result
                
            except Exception as e:
                # Calculate duration even for errors
                duration = time.time() - start_time
                
                # Log error
                logger.log_operation_error(op_name, e, duration=duration)
                raise
        
        return wrapper
    return decorator
