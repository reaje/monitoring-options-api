"""Application configuration using Pydantic Settings."""

from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # =====================================
    # SUPABASE CONFIGURATION
    # =====================================
    SUPABASE_URL: str
    SUPABASE_KEY: str
    SUPABASE_SERVICE_KEY: str
    DATABASE_URL: str

    # Database Connection Details
    DB_HOST: str = "aws-0-sa-east-1.pooler.supabase.com"
    DB_PORT: int = 5432
    DB_NAME: str = "postgres"
    DB_USER: str = "postgres.yzhqgoofrxixndfcfucz"
    DB_PASSWORD: str
    DB_SCHEMA: str = "monitoring_options_operations"
    DB_SSL_MODE: str = "require"
    DB_POOL_MIN: int = 2
    DB_POOL_MAX: int = 10

    # =====================================
    # COMMUNICATIONS API CONFIGURATION
    # =====================================
    COMM_API_URL: str
    COMM_API_KEY: str = ""  # Optional: If API uses API key instead of OAuth
    COMM_CLIENT_ID: str
    COMM_EMAIL: str
    COMM_PASSWORD: str

    # =====================================
    # APPLICATION CONFIGURATION
    # =====================================
    ENV: str = "development"
    DEBUG: bool = True
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000"

    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS origins string into list."""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]

    # =====================================
    # WORKER CONFIGURATION
    # =====================================
    MONITOR_INTERVAL_MINUTES: int = 5
    NOTIFIER_INTERVAL_SECONDS: int = 30
    MAX_NOTIFICATION_RETRIES: int = 3

    # =====================================
    # RULES ENGINE CONFIGURATION
    # =====================================
    DEFAULT_DELTA_THRESHOLD: float = 0.60
    DEFAULT_DTE_MIN: int = 3
    DEFAULT_DTE_MAX: int = 5
    DEFAULT_MIN_VOLUME: int = 1000
    DEFAULT_MAX_SPREAD: float = 0.05
    DEFAULT_MIN_OI: int = 5000

    # =====================================
    # LOGGING CONFIGURATION
    # =====================================
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"

    # =====================================
    # API DOCUMENTATION
    # =====================================
    ENABLE_DOCS: bool = True
    API_TITLE: str = "Monitoring Options API"
    API_VERSION: str = "1.0.0"
    API_DESCRIPTION: str = "API para monitoramento de operações com opções"

    # =====================================
    # RATE LIMITING
    # =====================================
    NOTIFY_RATE_LIMIT: int = 10
    API_RATE_LIMIT: int = 100

    # =====================================
    # SECURITY
    # =====================================
    JWT_SECRET: str = "your-super-secret-jwt-key-change-this-in-production"
    SESSION_TIMEOUT: int = 60

    # =====================================
    # MARKET DATA CONFIGURATION
    # =====================================
    MARKET_DATA_PROVIDER: str = "mock"
    MARKET_DATA_API_KEY: str = ""
    MARKET_DATA_REFRESH_INTERVAL: int = 60

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


# Singleton instance
settings = Settings()
