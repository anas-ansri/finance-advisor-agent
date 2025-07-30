"""
Logging utilities for better log readability and consistency.
"""

import logging
import time
from functools import wraps
from typing import Any, Callable, Dict, Optional
from uuid import UUID

from app.core.logging_config import get_request_logger


def log_function_call(logger: logging.Logger = None, level: str = "debug"):
    """
    Decorator to automatically log function calls with parameters and execution time.
    
    Args:
        logger: Logger instance to use. If None, uses function's module logger.
        level: Log level to use (debug, info, warning, error)
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            func_logger = logger or logging.getLogger(func.__module__)
            start_time = time.time()
            
            # Sanitize arguments for logging (avoid logging sensitive data)
            safe_kwargs = {k: v for k, v in kwargs.items() 
                          if not any(sensitive in k.lower() for sensitive in ['password', 'token', 'key', 'secret'])}
            
            getattr(func_logger, level)(
                f"🔧 Calling {func.__name__}",
                extra={
                    "function": func.__name__,
                    "module": func.__module__,
                    "args_count": len(args),
                    "kwargs": safe_kwargs
                }
            )
            
            try:
                result = await func(*args, **kwargs)
                execution_time = time.time() - start_time
                
                getattr(func_logger, level)(
                    f"✅ {func.__name__} completed successfully",
                    extra={
                        "function": func.__name__,
                        "execution_time": round(execution_time, 3),
                        "result_type": type(result).__name__
                    }
                )
                return result
                
            except Exception as e:
                execution_time = time.time() - start_time
                func_logger.error(
                    f"❌ {func.__name__} failed",
                    extra={
                        "function": func.__name__,
                        "execution_time": round(execution_time, 3),
                        "error_type": type(e).__name__,
                        "error_message": str(e)
                    },
                    exc_info=True
                )
                raise
                
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            func_logger = logger or logging.getLogger(func.__module__)
            start_time = time.time()
            
            safe_kwargs = {k: v for k, v in kwargs.items() 
                          if not any(sensitive in k.lower() for sensitive in ['password', 'token', 'key', 'secret'])}
            
            getattr(func_logger, level)(
                f"🔧 Calling {func.__name__}",
                extra={
                    "function": func.__name__,
                    "module": func.__module__,
                    "args_count": len(args),
                    "kwargs": safe_kwargs
                }
            )
            
            try:
                result = func(*args, **kwargs)
                execution_time = time.time() - start_time
                
                getattr(func_logger, level)(
                    f"✅ {func.__name__} completed successfully",
                    extra={
                        "function": func.__name__,
                        "execution_time": round(execution_time, 3),
                        "result_type": type(result).__name__
                    }
                )
                return result
                
            except Exception as e:
                execution_time = time.time() - start_time
                func_logger.error(
                    f"❌ {func.__name__} failed",
                    extra={
                        "function": func.__name__,
                        "execution_time": round(execution_time, 3),
                        "error_type": type(e).__name__,
                        "error_message": str(e)
                    },
                    exc_info=True
                )
                raise
        
        # Return appropriate wrapper based on function type
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


def log_db_operation(operation_type: str, table: str = None):
    """
    Decorator specifically for database operations.
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            logger = logging.getLogger(func.__module__)
            start_time = time.time()
            
            logger.debug(
                f"🗄️ DB {operation_type} started",
                extra={
                    "operation": operation_type,
                    "table": table or "unknown",
                    "function": func.__name__
                }
            )
            
            try:
                result = await func(*args, **kwargs)
                execution_time = time.time() - start_time
                
                # Try to get result count if it's a list or has a count method
                result_info = {}
                if hasattr(result, '__len__'):
                    result_info["count"] = len(result)
                elif hasattr(result, 'rowcount'):
                    result_info["affected_rows"] = result.rowcount
                
                logger.debug(
                    f"✅ DB {operation_type} completed",
                    extra={
                        "operation": operation_type,
                        "table": table or "unknown",
                        "execution_time": round(execution_time, 3),
                        **result_info
                    }
                )
                return result
                
            except Exception as e:
                execution_time = time.time() - start_time
                logger.error(
                    f"❌ DB {operation_type} failed",
                    extra={
                        "operation": operation_type,
                        "table": table or "unknown",
                        "execution_time": round(execution_time, 3),
                        "error_type": type(e).__name__,
                        "error_message": str(e)
                    },
                    exc_info=True
                )
                raise
        
        return wrapper
    return decorator


def log_api_call(service_name: str):
    """
    Decorator for external API calls.
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            logger = logging.getLogger(func.__module__)
            start_time = time.time()
            
            logger.info(
                f"🌐 External API call to {service_name}",
                extra={
                    "service": service_name,
                    "function": func.__name__
                }
            )
            
            try:
                result = await func(*args, **kwargs)
                execution_time = time.time() - start_time
                
                logger.info(
                    f"✅ API call to {service_name} successful",
                    extra={
                        "service": service_name,
                        "execution_time": round(execution_time, 3),
                        "response_type": type(result).__name__
                    }
                )
                return result
                
            except Exception as e:
                execution_time = time.time() - start_time
                logger.error(
                    f"❌ API call to {service_name} failed",
                    extra={
                        "service": service_name,
                        "execution_time": round(execution_time, 3),
                        "error_type": type(e).__name__,
                        "error_message": str(e)
                    },
                    exc_info=True
                )
                raise
        
        return wrapper
    return decorator


def sanitize_for_logging(data: Any, max_length: int = 200) -> Any:
    """
    Sanitize data for safe logging by removing sensitive information
    and truncating long strings.
    """
    if isinstance(data, dict):
        sanitized = {}
        for key, value in data.items():
            # Skip sensitive keys
            if any(sensitive in key.lower() for sensitive in 
                   ['password', 'token', 'key', 'secret', 'auth', 'credential']):
                sanitized[key] = "[REDACTED]"
            else:
                sanitized[key] = sanitize_for_logging(value, max_length)
        return sanitized
    
    elif isinstance(data, list):
        return [sanitize_for_logging(item, max_length) for item in data[:10]]  # Limit to first 10 items
    
    elif isinstance(data, str):
        if len(data) > max_length:
            return data[:max_length] + "..."
        return data
    
    elif isinstance(data, (int, float, bool, type(None))):
        return data
    
    elif isinstance(data, UUID):
        return str(data)
    
    else:
        # For other objects, try to get a string representation
        try:
            str_repr = str(data)
            if len(str_repr) > max_length:
                return str_repr[:max_length] + "..."
            return str_repr
        except:
            return f"[{type(data).__name__} object]"


def create_operation_logger(operation_name: str, module_name: str, **context) -> logging.Logger:
    """
    Create a logger with operation-specific context.
    
    Args:
        operation_name: Name of the operation being performed
        module_name: Module name for the logger
        **context: Additional context to include in logs
    
    Returns:
        Logger instance with operation context
    """
    logger = logging.getLogger(module_name)
    
    # Create a custom logger adapter with operation context
    class OperationLoggerAdapter(logging.LoggerAdapter):
        def process(self, msg, kwargs):
            if 'extra' not in kwargs:
                kwargs['extra'] = {}
            
            kwargs['extra'].update({
                'operation': operation_name,
                **context,
                **self.extra
            })
            return msg, kwargs
    
    return OperationLoggerAdapter(logger, context)


# Common logging patterns for the application
class LogPatterns:
    """Common logging patterns for consistent messaging."""
    
    @staticmethod
    def user_action(logger: logging.Logger, user_id: Any, action: str, **details):
        """Log user actions."""
        logger.info(
            f"👤 User action: {action}",
            extra={
                "user_id": str(user_id),
                "action": action,
                **sanitize_for_logging(details)
            }
        )
    
    @staticmethod
    def data_processing(logger: logging.Logger, data_type: str, count: int, **details):
        """Log data processing operations."""
        logger.info(
            f"⚙️ Processing {count} {data_type} records",
            extra={
                "data_type": data_type,
                "count": count,
                **sanitize_for_logging(details)
            }
        )
    
    @staticmethod
    def ai_interaction(logger: logging.Logger, model: str, prompt_length: int, **details):
        """Log AI model interactions."""
        logger.info(
            f"🤖 AI interaction with {model}",
            extra={
                "model": model,
                "prompt_length": prompt_length,
                **sanitize_for_logging(details)
            }
        )
    
    @staticmethod
    def cache_operation(logger: logging.Logger, operation: str, key: str, hit: bool = None, **details):
        """Log caching operations."""
        hit_status = "HIT" if hit is True else "MISS" if hit is False else "SET"
        logger.debug(
            f"🗃️ Cache {operation}: {key} ({hit_status})",
            extra={
                "cache_operation": operation,
                "cache_key": key,
                "cache_hit": hit,
                **sanitize_for_logging(details)
            }
        )
