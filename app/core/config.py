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
    PORT: int = 8000
    
    # Documentation settings
    DOCS_URL: str = "/docs"
    REDOC_URL: str = "/redoc"
    
    # CORS settings
    CORS_ORIGINS: List[str] = ["http://localhost:3000"]
    
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
    
    # Supabase settings
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "")
    
    # Database settings
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./app.db")
    
    # Logging settings
    LOG_LEVEL: str = "INFO"
    
    # AI model settings
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
    DEFAULT_MODEL: str = "gpt-4o"
    
    class Config:
        case_sensitive = True
        env_file = ".env"
        extra = "allow"  # Allow extra fields during transition


settings = Settings()
