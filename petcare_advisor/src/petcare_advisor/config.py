"""Configuration management for petcare advisor."""

import os
from typing import Optional
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # API Keys - read from environment, support both VITE_ and non-VITE_ prefixes
    openai_api_key: Optional[str] = None
    gemini_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    
    def __init__(self, **kwargs):
        # Load .env file first (override=True to prioritize .env over system env)
        from dotenv import load_dotenv
        load_dotenv(override=True)
        
        # Read from environment variables (support both VITE_ and non-VITE_ prefixes)
        # Priority: VITE_ prefixed > non-VITE_ prefixed
        openai_key = os.getenv("VITE_OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY")
        gemini_key = os.getenv("VITE_GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY")
        anthropic_key = os.getenv("VITE_ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
        
        # Set values
        if openai_key:
            kwargs.setdefault("openai_api_key", openai_key)
        if gemini_key:
            kwargs.setdefault("gemini_api_key", gemini_key)
        if anthropic_key:
            kwargs.setdefault("anthropic_api_key", anthropic_key)
        
        super().__init__(**kwargs)
    
    # Model Configuration
    model_config_symptom_intake: str = os.getenv("MODEL_CONFIG_SYMPTOM_INTAKE", "gemini-1.5-flash")
    model_config_vision: str = os.getenv("MODEL_CONFIG_VISION", "gpt-4o")
    model_config_medical: str = os.getenv("MODEL_CONFIG_MEDICAL", "claude-sonnet-4-20250514")
    model_config_triage: str = os.getenv("MODEL_CONFIG_TRIAGE", "claude-sonnet-4-20250514")
    model_config_careplan: str = os.getenv("MODEL_CONFIG_CAREPLAN", "gemini-1.5-pro")
    model_config_root: str = os.getenv("MODEL_CONFIG_ROOT", "gpt-4")
    
    # API Configuration
    api_host: str = os.getenv("API_HOST", "0.0.0.0")
    api_port: int = int(os.getenv("API_PORT", "8000"))
    api_reload: bool = os.getenv("API_RELOAD", "true").lower() == "true"
    
    # Logging
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"  # Ignore extra fields like VITE_ prefixed vars


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get the global settings instance.
    
    Returns:
        Settings instance
    """
    return settings

