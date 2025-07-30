import json
import logging
import sys
from datetime import datetime
from typing import Dict, Any

from app.core.config import settings


class ColoredFormatter(logging.Formatter):
    """
    Custom colored formatter for development logs with better readability.
    """
    
    # ANSI color codes
    COLORS = {
        'DEBUG': '\033[36m',     # Cyan
        'INFO': '\033[32m',      # Green
        'WARNING': '\033[33m',   # Yellow
        'ERROR': '\033[31m',     # Red
        'CRITICAL': '\033[35m',  # Magenta
        'RESET': '\033[0m'       # Reset
    }
    
    def format(self, record):
        # Add color to log level
        level_color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
        colored_level = f"{level_color}{record.levelname:8}{self.COLORS['RESET']}"
        
        # Format timestamp
        timestamp = datetime.fromtimestamp(record.created).strftime('%H:%M:%S.%f')[:-3]
        
        # Build the base message
        base_msg = f"{timestamp} | {colored_level} | {record.name:25} | {record.getMessage()}"
        
        # Add extra context if available
        extras = []
        if hasattr(record, "request_id") and record.request_id:
            extras.append(f"req_id={record.request_id}")
        if hasattr(record, "user_id"):
            extras.append(f"user={record.user_id}")
        if hasattr(record, "endpoint"):
            extras.append(f"endpoint={record.endpoint}")
        if hasattr(record, "process_time"):
            extras.append(f"time={record.process_time:.3f}s")
        if hasattr(record, "status_code"):
            extras.append(f"status={record.status_code}")
            
        if extras:
            base_msg += f" [{', '.join(extras)}]"
            
        # Add exception info if available
        if record.exc_info:
            base_msg += f"\n{self.formatException(record.exc_info)}"
            
        return base_msg


class StructuredJsonFormatter(logging.Formatter):
    """
    Enhanced JSON formatter for production logs with better structure.
    """
    def format(self, record):
        log_record = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "source": {
                "module": record.module,
                "function": record.funcName,
                "line": record.lineno,
                "file": record.pathname
            },
            "process": {
                "pid": record.process,
                "thread": record.thread,
                "thread_name": record.threadName
            }
        }
        
        # Add request context
        request_context = {}
        if hasattr(record, "request_id") and record.request_id:
            request_context["request_id"] = record.request_id
        if hasattr(record, "user_id"):
            request_context["user_id"] = str(record.user_id)
        if hasattr(record, "endpoint"):
            request_context["endpoint"] = record.endpoint
        if hasattr(record, "method"):
            request_context["method"] = record.method
        if hasattr(record, "process_time"):
            request_context["process_time"] = round(record.process_time, 3)
        if hasattr(record, "status_code"):
            request_context["status_code"] = record.status_code
        if hasattr(record, "ip_address"):
            request_context["ip_address"] = record.ip_address
            
        if request_context:
            log_record["request"] = request_context
        
        # Add custom fields
        custom_fields = {}
        for key, value in record.__dict__.items():
            if key.startswith("custom_") and not key.startswith("_"):
                custom_fields[key.replace("custom_", "")] = value
        if custom_fields:
            log_record["custom"] = custom_fields
            
        # Add exception info if available
        if record.exc_info:
            log_record["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": self.formatException(record.exc_info).split('\n')
            }
            
        return json.dumps(log_record, indent=2 if settings.DEBUG else None)



class RequestLoggerAdapter(logging.LoggerAdapter):
    """
    Logger adapter that automatically includes request context.
    """
    def process(self, msg, kwargs):
        # Add request context to extra if not already present
        if 'extra' not in kwargs:
            kwargs['extra'] = {}
        
        # Merge adapter's extra context
        kwargs['extra'].update(self.extra)
        return msg, kwargs


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the specified name.
    """
    return logging.getLogger(name)


def get_request_logger(name: str, request_context: Dict[str, Any] = None) -> RequestLoggerAdapter:
    """
    Get a request-aware logger adapter.
    """
    logger = logging.getLogger(name)
    context = request_context or {}
    return RequestLoggerAdapter(logger, context)


def configure_logging():
    """
    Configure logging for the application with improved readability.
    """
    # Create root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(settings.LOG_LEVEL)
    
    # Clear any existing handlers
    root_logger.handlers.clear()
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(settings.LOG_LEVEL)
    
    # Create formatter based on configuration
    log_format = settings.LOG_FORMAT.lower()
    
    if log_format == "colored" or (log_format == "auto" and settings.DEBUG):
        # Use colored format for development
        formatter = ColoredFormatter()
        formatter_type = "colored"
    elif log_format == "json" or (log_format == "auto" and not settings.DEBUG):
        # Use structured JSON for production
        formatter = StructuredJsonFormatter()
        formatter_type = "json"
    else:
        # Simple format fallback
        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(name)-25s | %(message)s",
            datefmt="%H:%M:%S"
        )
        formatter_type = "simple"
    
    console_handler.setFormatter(formatter)
    
    # Add handler to root logger
    root_logger.addHandler(console_handler)
    
    # Configure third-party library logging
    third_party_loggers = [
        "uvicorn", "uvicorn.access", "uvicorn.error",
        "sqlalchemy.engine", "sqlalchemy.pool", "sqlalchemy.dialects",
        "httpx", "httpcore", "httpcore.connection", "httpcore.http11",
        "asyncio", "fastapi"
    ]
    
    for logger_name in third_party_loggers:
        logging.getLogger(logger_name).setLevel(logging.WARNING)
    
    # Set our application loggers to be more verbose in debug mode
    if settings.DEBUG:
        logging.getLogger("app").setLevel(logging.DEBUG)
    
    # Suppress function call logging if disabled
    if not getattr(settings, 'LOG_SHOW_FUNCTION_CALLS', False):
        # You can add logic here to suppress function call decorators
        pass
    
    root_logger.info("Logging configured successfully", extra={
        "debug_mode": settings.DEBUG,
        "log_level": settings.LOG_LEVEL,
        "log_format": settings.LOG_FORMAT,
        "formatter_type": formatter_type,
        "show_function_calls": getattr(settings, 'LOG_SHOW_FUNCTION_CALLS', False)
    })
