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

    QLOO_API_KEY: str = os.getenv("QLOO_API_KEY", "your_qloo_api_key_here")
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "your_gemini_api_key_here")
    
    class Config:
        case_sensitive = True
        env_file = ".env"
        extra = "allow"  # Allow extra fields during transition


settings = Settings()