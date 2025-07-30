# Enhanced Logging Guide

This application features an enhanced logging system designed for better readability and debugging. Here's how to use and configure it.

## Log Formats

### 1. Colored Format (Development)
Perfect for local development with color-coded log levels and emojis:
```
14:32:15.123 | INFO     | app.api.routes.health    | 🏥 Health check requested [req_id=a1b2c3d4, endpoint=/health]
14:32:15.125 | INFO     | app.api.routes.health    | ✅ Health check completed successfully [req_id=a1b2c3d4, time=0.002s, status=200]
```

### 2. Structured JSON (Production)
Machine-readable JSON format for production logging:
```json
{
  "timestamp": "2025-07-31T14:32:15.123Z",
  "level": "INFO",
  "logger": "app.api.routes.health",
  "message": "Health check requested",
  "request": {
    "request_id": "a1b2c3d4",
    "endpoint": "/health",
    "method": "GET",
    "process_time": 0.002,
    "status_code": 200
  }
}
```

### 3. Simple Format
Clean, simple format without colors:
```
14:32:15 | INFO     | app.api.routes.health    | Health check requested
```

## Configuration

Control logging behavior through environment variables:

```bash
# Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
LOG_LEVEL=INFO

# Log format (auto, colored, json, simple)
# 'auto' uses colored in DEBUG mode, json in production
LOG_FORMAT=auto

# Show detailed function call logging (true/false)
LOG_SHOW_FUNCTION_CALLS=false

# Enable debug mode for colored logs and detailed output
DEBUG=true
```

## Using the Enhanced Logging

### Basic Usage
```python
import logging
from app.core.logging_config import get_logger

logger = get_logger(__name__)

# Standard logging with emoji indicators
logger.info("🚀 Service starting up")
logger.warning("⚠️ Configuration value missing, using default")
logger.error("❌ Operation failed")
```

### Request-Aware Logging
```python
from app.core.logging_config import get_request_logger

# In your route handlers
request_logger = get_request_logger(__name__, {
    "request_id": "abc123",
    "user_id": "user456",
    "endpoint": "/api/v1/users"
})

request_logger.info("Processing user request")
```

### Function Call Logging
```python
from app.core.logging_utils import log_function_call

@log_function_call(level="info")
async def fetch_user_data(user_id: str):
    # Function implementation
    return user_data
```

### Database Operation Logging
```python
from app.core.logging_utils import log_db_operation

@log_db_operation("SELECT", "users")
async def get_user_by_id(db: AsyncSession, user_id: str):
    # Database operation
    return user
```

### API Call Logging
```python
from app.core.logging_utils import log_api_call

@log_api_call("OpenAI API")
async def generate_ai_response(prompt: str):
    # External API call
    return response
```

### Pattern-Based Logging
```python
from app.core.logging_utils import LogPatterns

# User action logging
LogPatterns.user_action(logger, user_id="123", action="login", ip="192.168.1.1")

# Data processing logging
LogPatterns.data_processing(logger, data_type="transactions", count=150, source="bank_api")

# AI interaction logging
LogPatterns.ai_interaction(logger, model="gpt-4", prompt_length=1200, tokens_used=800)

# Cache operation logging
LogPatterns.cache_operation(logger, operation="GET", key="user:123:profile", hit=True)
```

## Log Levels and Emojis

The system uses emojis to make logs more scannable:

- 🚀 **Startup/Initialization**
- 🏥 **Health checks**
- 👤 **User actions**
- 🗄️ **Database operations**
- 🌐 **External API calls**
- 🤖 **AI interactions**
- 🗃️ **Cache operations**
- ⚙️ **Data processing**
- 🔧 **Function calls**
- ✅ **Success operations**
- ⚠️ **Warnings**
- ❌ **Errors/Failures**

## Request Tracking

Each request gets:
- **Request ID**: Unique identifier for tracing
- **Process Time**: How long the request took
- **Context**: User ID, endpoint, method, IP address
- **Status Codes**: Success/error indication

## Security Features

- **Sensitive Data Filtering**: Automatically redacts passwords, tokens, keys
- **Data Truncation**: Long strings are truncated to prevent log bloat
- **Safe Serialization**: Complex objects are safely converted to strings

## Performance Considerations

- **Conditional Logging**: Debug logs are only processed when debug mode is enabled
- **Lazy Evaluation**: Log messages use f-strings and extra parameters efficiently
- **Minimal Overhead**: Production JSON format is optimized for parsing

## Best Practices

1. **Use appropriate log levels**:
   - `DEBUG`: Detailed diagnostic information
   - `INFO`: General operational messages
   - `WARNING`: Potentially harmful situations
   - `ERROR`: Error events that still allow the application to continue
   - `CRITICAL`: Very serious error events

2. **Include context**: Always add relevant context using the `extra` parameter

3. **Use decorators**: Leverage the provided decorators for consistent logging

4. **Structure your messages**: Use clear, actionable log messages

5. **Test in both modes**: Verify logs work in both development (colored) and production (JSON) modes

## Troubleshooting

### Common Issues

1. **Colors not showing**: Make sure your terminal supports ANSI colors
2. **Too much noise**: Adjust LOG_LEVEL or disable LOG_SHOW_FUNCTION_CALLS
3. **JSON parsing errors**: Verify all logged data is JSON serializable

### Debugging Tips

1. Set `LOG_LEVEL=DEBUG` to see detailed information
2. Use `LOG_FORMAT=colored` for easier reading during development
3. Enable `LOG_SHOW_FUNCTION_CALLS=true` to trace function execution
4. Check the request_id to follow a request through the entire flow

## Examples

### Development Setup
```bash
export DEBUG=true
export LOG_LEVEL=DEBUG
export LOG_FORMAT=colored
export LOG_SHOW_FUNCTION_CALLS=true
```

### Production Setup
```bash
export DEBUG=false
export LOG_LEVEL=INFO
export LOG_FORMAT=json
export LOG_SHOW_FUNCTION_CALLS=false
```

This enhanced logging system provides better visibility into your application's behavior while maintaining performance and security.
