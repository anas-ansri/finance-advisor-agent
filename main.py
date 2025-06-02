import logging
import time
import asyncio
from contextlib import asynccontextmanager
import os

import uvicorn
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import api_router
from app.core.config import settings
from app.core.logging_config import configure_logging
from app.db.database import init_db

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
    try:
        # Initialize database with timeout
        async with asyncio.timeout(10):  # 10 second timeout for database initialization
            await init_db()
        logger.info("Database initialized successfully")
    except asyncio.TimeoutError:
        logger.error("Database initialization timed out")
        raise
    except Exception as e:
        logger.error(f"Failed to initialize database: {str(e)}")
        raise
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


# Add request ID middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """
    Middleware to add process time header and log request details.
    """
    start_time = time.time()
    request_id = request.headers.get("X-Request-ID", "")
    logger.info(
        f"Request started: {request.method} {request.url.path}",
        extra={"request_id": request_id},
    )
    
    try:
        response = await call_next(request)
        process_time = time.time() - start_time
        response.headers["X-Process-Time"] = str(process_time)
        logger.info(
            f"Request completed: {request.method} {request.url.path} - {response.status_code}",
            extra={"request_id": request_id, "process_time": process_time},
        )
        return response
    except Exception as e:
        logger.exception(
            f"Request failed: {request.method} {request.url.path}",
            extra={"request_id": request_id},
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Internal server error"},
        )


# Include API routes
app.include_router(api_router, prefix=settings.API_PREFIX)


# Health check endpoint
@app.get("/health", tags=["Health"])
async def health_check():
    """
    Health check endpoint to verify the service is running.
    """
    return {"status": "healthy"}


if __name__ == "__main__":
    try:
        port = int(os.environ.get("PORT", settings.PORT))
        uvicorn.run(
            "main:app",
            host=settings.HOST,
            port=port,
            reload=settings.DEBUG,
            log_level=settings.LOG_LEVEL.lower(),
            timeout_keep_alive=30,  # Reduce keep-alive timeout
            limit_concurrency=100,  # Limit concurrent connections
            backlog=2048,  # Increase backlog
        )
    except Exception as e:
        logger.error(f"Failed to start application: {str(e)}")
        raise
