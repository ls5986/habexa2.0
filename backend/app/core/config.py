from pydantic_settings import BaseSettings
from typing import Optional
from pathlib import Path
import os

# Find project root (where .env file is)
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
ENV_FILE = PROJECT_ROOT / ".env"


class Settings(BaseSettings):
    # Supabase
    SUPABASE_URL: str
    SUPABASE_ANON_KEY: str
    SUPABASE_SERVICE_ROLE_KEY: str
    SUPABASE_JWT_SECRET: Optional[str] = None  # Not actually used - Supabase client handles JWT internally
    SUPABASE_DATABASE_PASSWORD: Optional[str] = None

    # Amazon SP-API (Self-authorized - no OAuth needed)
    SPAPI_APP_ID: Optional[str] = None
    SPAPI_LWA_CLIENT_ID: Optional[str] = None
    SPAPI_LWA_CLIENT_SECRET: Optional[str] = None
    SPAPI_REFRESH_TOKEN: Optional[str] = None
    MARKETPLACE_ID: str = "ATVPDKIKX0DER"
    SELLER_ID: Optional[str] = None
    # AWS IAM Credentials (for SP-API request signing)
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    AWS_REGION: str = "us-east-1"
    SP_API_ROLE_ARN: Optional[str] = None

    # ASIN Data API
    ASIN_DATA_API_KEY: str

    # Keepa
    KEEPA_API_KEY: Optional[str] = None

    # OpenAI
    OPENAI_API_KEY: str

    # Telegram
    TELEGRAM_API_ID: Optional[str] = None
    TELEGRAM_API_HASH: Optional[str] = None

    # App
    SECRET_KEY: str
    FRONTEND_URL: str = "http://localhost:5173"
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
    STRIPE_SUCCESS_URL: str = "http://localhost:5173/billing/success"
    STRIPE_CANCEL_URL: str = "http://localhost:5173/billing/cancel"

    class Config:
        env_file = str(ENV_FILE) if ENV_FILE.exists() else ".env"
        case_sensitive = True
        extra = "ignore"  # Ignore extra fields in .env


settings = Settings()

