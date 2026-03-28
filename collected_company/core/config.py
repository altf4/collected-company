"""Application configuration."""

from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Database
    database_url: str = "sqlite+aiosqlite:///./collected_company.db"

    # Scryfall API
    scryfall_api_url: str = "https://api.scryfall.com"

    # Caching
    cache_ttl_minutes: int = 15

    # Scraping
    scraper_timeout_seconds: int = 15
    scraper_max_retries: int = 1

    # Logging
    log_level: str = "INFO"

    # Sentry (optional)
    sentry_dsn: Optional[str] = None

    # CORS
    cors_origins: list[str] = ["*"]


# Global settings instance
settings = Settings()
