import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    APP_NAME: str = "EVE Healthcare API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"
    ENVIRONMENT: str = "development"  # development | staging | production

    # Database
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/eve_healthcare"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    CACHE_TTL_SECONDS: int = 600  # 10 minutes for catalogue endpoints

    # JWT
    JWT_SECRET_KEY: str = "super-secret-jwt-key-change-in-production-must-be-32-chars"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    # Payment Simulation
    PAYMENT_SUCCESS_RATE: float = 0.8
    WEBHOOK_SECRET_KEY: str = "webhook-hmac-secret-key-change-in-production"
    ENABLE_WEBHOOK_HMAC: bool = False  # Enable in production

    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_LOGIN: str = "5/minute"
    RATE_LIMIT_PAYMENT: str = "20/minute"
    RATE_LIMIT_DEFAULT: str = "100/minute"

    # Background Jobs
    PENDING_BOOKING_TIMEOUT_MINUTES: int = 15  # Auto-cancel after this long in PENDING state

    # Celery
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"  # json | text


settings = Settings()
