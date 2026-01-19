"""
OncoRAD Configuration Module

Centralized configuration management using pydantic-settings.
"""

import os
from typing import Optional, List
from functools import lru_cache

try:
    from pydantic_settings import BaseSettings
except ImportError:
    from pydantic import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application Info
    app_name: str = "OncoRAD Clinical Reasoning Engine"
    app_version: str = "0.2.0"
    debug: bool = False

    # API Configuration
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_prefix: str = "/api/v1"

    # LLM Configuration
    llm_provider: str = "anthropic"  # "anthropic" or "openai"
    llm_model: Optional[str] = None  # None uses default for provider
    anthropic_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None

    # Vector Store Configuration
    vector_db_path: str = "./data/vector_db"
    embedding_model: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    use_gpu: bool = False

    # Document Processing
    documents_path: str = "./data/documents"
    chunk_size: int = 1000
    chunk_overlap: int = 200

    # Query Engine Configuration
    max_search_results: int = 10
    min_relevance_score: float = 0.3
    validate_responses: bool = True
    default_language: str = "es"

    # CORS Configuration (for iOS app)
    cors_origins: List[str] = ["*"]
    cors_allow_credentials: bool = True
    cors_allow_methods: List[str] = ["*"]
    cors_allow_headers: List[str] = ["*"]

    # Security
    api_key_header: str = "X-API-Key"
    require_api_key: bool = False
    allowed_api_keys: List[str] = []

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"

    @property
    def effective_api_key(self) -> Optional[str]:
        """Get the API key for the configured LLM provider."""
        if self.llm_provider == "anthropic":
            return self.anthropic_api_key or os.getenv("ANTHROPIC_API_KEY")
        elif self.llm_provider == "openai":
            return self.openai_api_key or os.getenv("OPENAI_API_KEY")
        return None


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Default settings instance
settings = get_settings()
