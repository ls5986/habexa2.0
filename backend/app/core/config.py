from pydantic_settings import BaseSettings
from pydantic import ConfigDict
from typing import Optional
from pathlib import Path
import os
from dotenv import load_dotenv

# Find project root (where .env file is)
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
ENV_FILE = PROJECT_ROOT / ".env"

# Explicitly load .env file
if ENV_FILE.exists():
    load_dotenv(ENV_FILE)
    print(f"✅ Loaded .env from: {ENV_FILE}")
else:
    # Try backend/.env as fallback
    BACKEND_ENV = Path(__file__).parent.parent.parent / ".env"
    if BACKEND_ENV.exists():
        load_dotenv(BACKEND_ENV)
        print(f"✅ Loaded .env from: {BACKEND_ENV}")
    else:
        print(f"⚠️  No .env file found at {ENV_FILE} or {BACKEND_ENV}")


class Settings(BaseSettings):
    # Supabase
    SUPABASE_URL: str
    SUPABASE_ANON_KEY: str
    SUPABASE_SERVICE_ROLE_KEY: str
    SUPABASE_JWT_SECRET: Optional[str] = None  # Not actually used - Supabase client handles JWT internally
    SUPABASE_DATABASE_PASSWORD: Optional[str] = None

    # Amazon SP-API (Hybrid: App credentials for public data, User credentials for seller data)
    SP_API_LWA_APP_ID: Optional[str] = None  # App-level LWA App ID
    SP_API_LWA_CLIENT_SECRET: Optional[str] = None  # App-level LWA Client Secret
    SP_API_REFRESH_TOKEN: Optional[str] = None  # App-level refresh token (for public data)
    # Legacy names (for backward compatibility)
    SPAPI_APP_ID: Optional[str] = None  # SP-API Application ID (for OAuth)
    SPAPI_LWA_CLIENT_ID: Optional[str] = None
    SPAPI_LWA_CLIENT_SECRET: Optional[str] = None
    SPAPI_REFRESH_TOKEN: Optional[str] = None
    MARKETPLACE_ID: str = "ATVPDKIKX0DER"
    SELLER_ID: Optional[str] = None
    # AWS IAM Credentials (for SP-API request signing - if needed)
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    AWS_REGION: str = "us-east-1"
    SP_API_ROLE_ARN: Optional[str] = None

    # ASIN Data API (Optional - only needed if using asin_data_client, but we use batch_analyzer)
    ASIN_DATA_API_KEY: Optional[str] = None

    # Keepa (REQUIRED for analysis workers - used by batch_analyzer and keepa_analysis_service)
    KEEPA_API_KEY: Optional[str] = None

    # OpenAI (REQUIRED for telegram worker - used for message extraction)
    OPENAI_API_KEY: Optional[str] = None

    # Telegram
    TELEGRAM_API_ID: Optional[str] = None
    TELEGRAM_API_HASH: Optional[str] = None

    # App
    SECRET_KEY: Optional[str] = None  # Optional to allow workers to start, but required for JWT/encryption
    FRONTEND_URL: str = "http://localhost:3002"
    BACKEND_URL: str = "http://localhost:8000"
    API_V1_PREFIX: str = "/api/v1"
    
    # Stripe
    STRIPE_SECRET_KEY: Optional[str] = None
    STRIPE_PUBLISHABLE_KEY: Optional[str] = None
    STRIPE_WEBHOOK_SECRET: Optional[str] = None
    STRIPE_PRICE_STARTER_MONTHLY: Optional[str] = None
    STRIPE_PRICE_STARTER_YEARLY: Optional[str] = None
    STRIPE_PRICE_PRO_MONTHLY: Optional[str] = None
    STRIPE_PRICE_PRO_YEARLY: Optional[str] = None
    STRIPE_PRICE_AGENCY_MONTHLY: Optional[str] = None
    STRIPE_PRICE_AGENCY_YEARLY: Optional[str] = None
    STRIPE_SUCCESS_URL: str = "http://localhost:3002/billing/success"
    STRIPE_CANCEL_URL: str = "http://localhost:3002/billing/cancel"
    
    # Super Admins (comma-separated in env)
    SUPER_ADMIN_EMAILS: str = "lindsey@letsclink.com"  # Default, can be overridden in env
    
    # Email service (optional - for transactional emails)
    EMAIL_PROVIDER: Optional[str] = None  # resend, sendgrid, postmark, ses
    EMAIL_API_KEY: Optional[str] = None
    EMAIL_FROM: str = "noreply@habexa.com"
    EMAIL_FROM_NAME: str = "Habexa"
    
    # Redis (Optional - for caching)
    REDIS_URL: Optional[str] = None  # e.g., "redis://localhost:6379/0" or "rediss://..." for SSL
    
    # Celery Configuration
    CELERY_WORKERS: int = 8  # Number of parallel workers for batch processing
    CELERY_PROCESS_BATCH_SIZE: int = 100  # Batch size for processing (matches Keepa batch size)
    
    # Cache Configuration
    KEEPA_CACHE_HOURS: int = 24  # Hours to cache Keepa data
    
    # API Rate Limits
    SP_API_BATCH_SIZE: int = 20  # SP-API batch size limit
    KEEPA_BATCH_SIZE: int = 100  # Keepa API batch size limit
    
    # Testing/Development
    TEST_MODE: bool = False  # Enable test mode (bypasses auth for certain endpoints)
    ALLOWED_IPS: Optional[str] = None  # Comma-separated list of IPs allowed in test mode (e.g., "1.2.3.4,5.6.7.8")

    @property
    def super_admin_list(self) -> list[str]:
        """Parse comma-separated super admin emails."""
        if not self.SUPER_ADMIN_EMAILS:
            return []
        return [e.strip().lower() for e in self.SUPER_ADMIN_EMAILS.split(",") if e.strip()]

    model_config = ConfigDict(
        env_file=str(ENV_FILE) if ENV_FILE.exists() else ".env",
        case_sensitive=True,
        extra="ignore"  # Ignore extra fields in .env
    )


settings = Settings()

