import logging
import time
import uuid
from contextlib import asynccontextmanager
import os

import uvicorn
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.api.routes import api_router
from app.core.config import settings
from app.core.logging_config import configure_logging, get_request_logger

# Configure logging
configure_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan events for the FastAPI application.
    This handles startup and shutdown events.
    """
    # Startup events
    logger.info("Starting up Savvy APIs service")
    yield
    # Shutdown events
    logger.info("Shutting down Savvy APIs service")


app = FastAPI(
    title=settings.PROJECT_NAME,
    description=settings.PROJECT_DESCRIPTION,
    version=settings.VERSION,
    docs_url=settings.DOCS_URL,
    redoc_url=settings.REDOC_URL,
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Add enhanced request logging middleware
@app.middleware("http")
async def enhanced_request_logging_middleware(request: Request, call_next):
    """
    Enhanced middleware for comprehensive request logging with better context.
    """
    # Generate or extract request ID
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())[:8]
    
    # Extract client information
    client_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("User-Agent", "unknown")
    
    # Create request context for logging
    request_context = {
        "request_id": request_id,
        "method": request.method,
        "endpoint": str(request.url.path),
        "ip_address": client_ip,
        "custom_user_agent": user_agent
    }
    
    # Get request-aware logger
    request_logger = get_request_logger(__name__, request_context)
    
    # Log request start
    start_time = time.time()
    request_logger.info(
        f"🚀 Request started: {request.method} {request.url.path}",
        extra={
            "query_params": dict(request.query_params) if request.query_params else None,
            "path_params": request.path_params if request.path_params else None,
        }
    )
    
    try:
        # Process request
        response = await call_next(request)
        
        # Calculate processing time
        process_time = time.time() - start_time
        
        # Add response headers
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time"] = str(process_time)
        
        # Determine log level based on status code
        status_code = response.status_code
        if status_code >= 500:
            log_level = "error"
        elif status_code >= 400:
            log_level = "warning"
        else:
            log_level = "info"
            
        # Log successful completion
        getattr(request_logger, log_level)(
            f"✅ Request completed: {request.method} {request.url.path} → {status_code}",
            extra={
                "status_code": status_code,
                "process_time": process_time,
                "response_size": response.headers.get("content-length", "unknown")
            }
        )
        
        return response
        
    except Exception as e:
        process_time = time.time() - start_time
        
        # Log error with full context
        request_logger.error(
            f"❌ Request failed: {request.method} {request.url.path} → {type(e).__name__}",
            extra={
                "process_time": process_time,
                "error_type": type(e).__name__,
                "error_message": str(e),
            },
            exc_info=True
        )
        
        # Return generic error response
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "detail": "Internal server error",
                "request_id": request_id,
                "timestamp": time.time()
            },
            headers={"X-Request-ID": request_id}
        )


# Include API routes
app.include_router(api_router, prefix=settings.API_PREFIX)


# Health check endpoint
@app.get("/health", tags=["Health"])
async def health_check(request: Request):
    """
    Enhanced health check endpoint with detailed logging.
    """
    # Get request-aware logger
    request_context = {
        "endpoint": "/health",
        "method": "GET"
    }
    health_logger = get_request_logger(__name__, request_context)
    
    health_logger.info("🏥 Health check requested")
    
    try:
        # You can add more health checks here (database, external services, etc.)
        health_status = {
            "status": "healthy",
            "timestamp": time.time(),
            "version": settings.VERSION,
            "environment": "development" if settings.DEBUG else "production"
        }
        
        health_logger.info(
            "✅ Health check completed successfully",
            extra={
                "health_status": health_status["status"],
                "version": health_status["version"]
            }
        )
        
        return health_status
        
    except Exception as e:
        health_logger.error(
            "❌ Health check failed",
            extra={
                "error_type": type(e).__name__,
                "error_message": str(e)
            },
            exc_info=True
        )
        raise


if __name__ == "__main__":
    try:
        port = int(os.environ.get("PORT", settings.PORT))
        uvicorn.run(
            "main:app",
            host=settings.HOST,
            port=port,
            reload=settings.DEBUG,
            log_level=settings.LOG_LEVEL.lower(),
        )
    except Exception as e:
        logger.error(f"Failed to start application: {str(e)}")
        raise
