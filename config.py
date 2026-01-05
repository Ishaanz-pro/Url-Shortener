from pydantic_settings import BaseSettings
from typing import Optional
import os

class Settings(BaseSettings):
    """Application configuration"""
    
    # Database
    database_url: str = "postgresql://shortener:shortener_pass@localhost:5432/url_shortener_db"
    
    # Redis
    redis_url: str = "redis://localhost:6379/0"
    redis_cache_expiry: int = 86400  # 24 hours
    
    # JWT
    secret_key: str = "change-me-in-production-use-strong-secret"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # API
    api_title: str = "URL Shortener API"
    api_version: str = "1.0.0"
    debug: bool = False
    
    # Rate Limiting
    rate_limit_requests: int = 100
    rate_limit_period_seconds: int = 60
    
    # Celery
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"
    
    # Environment
    environment: str = "development"
    
    # Shortener Domain
    shortener_domain: str = "http://localhost:8000"
    
    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings()
