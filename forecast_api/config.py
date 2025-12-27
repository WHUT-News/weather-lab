"""
Configuration management for FastAPI server.
Loads settings from environment variables with validation.
"""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # API Configuration
    API_TITLE: str = "Weather Forecast API"
    API_VERSION: str = "1.0.0"
    API_DESCRIPTION: str = "REST API for weather forecast retrieval"

    # Server Configuration
    PORT: int = 8000
    RELOAD: bool = False

    # CORS Configuration
    CORS_ORIGINS: list[str] = ["*"]
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: list[str] = ["GET", "OPTIONS"]
    CORS_ALLOW_HEADERS: list[str] = ["*"]

    # Cloud SQL Configuration
    GOOGLE_CLOUD_PROJECT: str
    GOOGLE_CLOUD_LOCATION: str = "us-central1"
    CLOUD_SQL_INSTANCE: str = "weather-forecasts"
    CLOUD_SQL_DB: str = "weather"
    CLOUD_SQL_USER: str = "postgres"
    CLOUD_SQL_PASSWORD: str

    # Agent Engine Configuration
    AGENT_ENGINE_ID: Optional[str] = None

    # Logging
    LOG_LEVEL: str = "INFO"

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
