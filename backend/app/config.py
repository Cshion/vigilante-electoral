"""Configuration settings for the application."""
from pydantic_settings import BaseSettings
import logging

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """Application settings from environment variables."""
    
    # API Configuration
    APP_NAME: str = "Vigilante Electoral"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # CORS Configuration - set via environment variable
    # Format: comma-separated list of origins
    # Example: ALLOWED_ORIGINS="https://app.com,https://api.com,http://localhost:3000"
    # Use "*" to allow all origins (development only)
    # Defaults to localhost for development if not set
    ALLOWED_ORIGINS: str = "http://localhost:3000,http://localhost:8000,http://127.0.0.1:3000,http://127.0.0.1:8000"
    
    # Optional: regex pattern for dynamic origins (e.g., Vercel previews)
    # Example: CORS_ORIGIN_REGEX="https://vigilante-electoral.*\.vercel\.app"
    CORS_ORIGIN_REGEX: str = ""
    
    # Database Configuration
    SUPABASE_URL: str = ""
    SUPABASE_KEY: str = ""
    
    # ONPE API Configuration  
    ONPE_BASE_URL: str = "https://resultadoelectoral.onpe.gob.pe"
    
    # Scraper Configuration
    SCRAPE_INTERVAL_MINUTES: int = 15
    TIMEOUT_SECONDS: int = 30
    
    # Cron protection
    CRON_SECRET: str = ""
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()

# Validate CORS config - warn if not set in production
if not settings.ALLOWED_ORIGINS and not settings.DEBUG:
    logger.warning(
        "ALLOWED_ORIGINS not set. CORS will block all cross-origin requests. "
        "Set ALLOWED_ORIGINS env var (comma-separated origins, or '*' for all)."
    )
