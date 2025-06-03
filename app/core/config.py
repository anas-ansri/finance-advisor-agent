import os
from typing import List, Optional, Union

from pydantic import AnyHttpUrl, validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Application settings.
    
    These settings can be configured using environment variables.
    """
    # API settings
    API_PREFIX: str = "/api/v1"
    PROJECT_NAME: str = "Savvy APIs"
    PROJECT_DESCRIPTION: str = "Backend API for AI agent functionality"
    VERSION: str = "0.1.0"
    DEBUG: bool = False
    HOST: str = "0.0.0.0"
    PORT: int = int(os.getenv("PORT", "5000"))
    
    # Documentation settings
    DOCS_URL: str = "/docs"
    REDOC_URL: str = "/redoc"
    
    # CORS settings
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "https://savvy-finance.vercel.app",
        "https://*.herokuapp.com",  # Allow all Heroku subdomains
        "http://localhost:5000",    # Allow local Swagger UI
        "http://localhost:8000",    # Allow alternative local port
    ]
    
    @validator("CORS_ORIGINS", pre=True)
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        """
        Parse CORS origins from string or list.
        """
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)
    
    # Database settings
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql+asyncpg://anas@localhost:5432/finance_advisor")
    TEST_DATABASE_URL: str = os.getenv("TEST_DATABASE_URL", "postgresql+asyncpg://anas@localhost:5432/finance_advisor_test")
    
    @validator("DATABASE_URL", pre=True)
    def assemble_db_url(cls, v: str) -> str:
        """
        Convert Heroku's postgres:// URL to postgresql+asyncpg:// format and add SSL configuration
        """
        if not v:
            return v
            
        # Handle Heroku's postgres:// URL format
        if v.startswith("postgres://"):
            # Extract the components
            parts = v.replace("postgres://", "").split("@")
            if len(parts) == 2:
                auth, host = parts
                # Add SSL mode and other required parameters
                if "?" not in host:
                    host += "?sslmode=require&connect_timeout=10"
                elif "sslmode=" not in host:
                    host += "&sslmode=require&connect_timeout=10"
                # Reconstruct the URL with asyncpg
                v = f"postgresql+asyncpg://{auth}@{host}"
            else:
                # If the URL format is unexpected, just replace the prefix
                v = v.replace("postgres://", "postgresql+asyncpg://", 1)
                if "?" not in v:
                    v += "?sslmode=require&connect_timeout=10"
                elif "sslmode=" not in v:
                    v += "&sslmode=require&connect_timeout=10"
        
        return v
    
    # Logging settings
    LOG_LEVEL: str = "INFO"
    
    # AI model settings
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
    DEFAULT_MODEL: str = "gpt-4"
    
    # Supabase settings
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "")
    SUPABASE_TEST_URL: str = os.getenv("SUPABASE_TEST_URL", "")
    SUPABASE_TEST_KEY: str = os.getenv("SUPABASE_TEST_KEY", "")
    
    class Config:
        case_sensitive = True
        env_file = ".env"
        extra = "allow"  # Allow extra fields during transition


settings = Settings()
