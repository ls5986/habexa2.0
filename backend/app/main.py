from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from app.core.config import settings
from app.api.v1 import deals, analysis, suppliers, notifications, settings as api_settings, watchlist, orders, billing, telegram, amazon, keepa, debug, market, sp_api, products, brands, jobs, batch, buy_list, auth, users, upload, favorites
from app.middleware.performance import PerformanceMiddleware
import logging
from datetime import datetime
import os
import re

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Habexa API",
    description="Amazon Sourcing Intelligence Platform API",
    version="1.0.0"
)

# Performance monitoring - add FIRST to track all requests
app.add_middleware(PerformanceMiddleware)

# CORS - MUST be added before other middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.FRONTEND_URL,
        "http://localhost:3002",
        "http://localhost:5173",  # Legacy port
        "http://localhost:5189",  # Vite may use different ports
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Global exception handler to ensure CORS headers are always set
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Ensure CORS headers are set even on errors."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    origin = request.headers.get("origin")
    allowed_origin = origin if origin in [
        settings.FRONTEND_URL,
        "http://localhost:3002",
        "http://localhost:5173",
        "http://localhost:5189",
        "http://localhost:3000",
    ] else settings.FRONTEND_URL
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
        headers={
            "Access-Control-Allow-Origin": allowed_origin,
            "Access-Control-Allow-Credentials": "true",
        }
    )

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Ensure CORS headers are set on HTTP exceptions."""
    origin = request.headers.get("origin")
    allowed_origin = origin if origin in [
        settings.FRONTEND_URL,
        "http://localhost:3002",
        "http://localhost:5173",
        "http://localhost:5189",
        "http://localhost:3000",
    ] else settings.FRONTEND_URL
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers={
            "Access-Control-Allow-Origin": allowed_origin,
            "Access-Control-Allow-Credentials": "true",
        }
    )

# Include routers
app.include_router(deals.router, prefix=f"{settings.API_V1_PREFIX}/deals", tags=["deals"])
app.include_router(products.router, prefix=f"{settings.API_V1_PREFIX}", tags=["products"])
app.include_router(brands.router, prefix=f"{settings.API_V1_PREFIX}", tags=["brands"])
app.include_router(jobs.router, prefix=f"{settings.API_V1_PREFIX}", tags=["jobs"])
app.include_router(batch.router, prefix=f"{settings.API_V1_PREFIX}", tags=["batch"])
app.include_router(analysis.router, prefix=f"{settings.API_V1_PREFIX}/analyze", tags=["analysis"])
app.include_router(suppliers.router, prefix=f"{settings.API_V1_PREFIX}/suppliers", tags=["suppliers"])
app.include_router(notifications.router, prefix=f"{settings.API_V1_PREFIX}/notifications", tags=["notifications"])
app.include_router(api_settings.router, prefix=f"{settings.API_V1_PREFIX}/settings", tags=["settings"])
app.include_router(watchlist.router, prefix=f"{settings.API_V1_PREFIX}/watchlist", tags=["watchlist"])
app.include_router(buy_list.router, prefix=f"{settings.API_V1_PREFIX}/buy-list", tags=["buy-list"])
app.include_router(orders.router, prefix=f"{settings.API_V1_PREFIX}/orders", tags=["orders"])
app.include_router(billing.router, prefix=f"{settings.API_V1_PREFIX}/billing", tags=["billing"])
app.include_router(auth.router, prefix=f"{settings.API_V1_PREFIX}/auth", tags=["auth"])
app.include_router(users.router, prefix=f"{settings.API_V1_PREFIX}/users", tags=["users"])
app.include_router(favorites.router, prefix=f"{settings.API_V1_PREFIX}", tags=["favorites"])
app.include_router(telegram.router, prefix=f"{settings.API_V1_PREFIX}/integrations/telegram", tags=["telegram"])
app.include_router(amazon.router, prefix=f"{settings.API_V1_PREFIX}", tags=["amazon"])
app.include_router(keepa.router, prefix=f"{settings.API_V1_PREFIX}", tags=["keepa"])  # Router already has /keepa prefix
app.include_router(market.router, prefix=f"{settings.API_V1_PREFIX}", tags=["market"])
app.include_router(sp_api.router, prefix=f"{settings.API_V1_PREFIX}", tags=["sp-api"])
app.include_router(debug.router, prefix=f"{settings.API_V1_PREFIX}/debug", tags=["debug"])
app.include_router(upload.router, prefix=f"{settings.API_V1_PREFIX}", tags=["upload"])


@app.get("/")
async def root():
    return {"message": "Habexa API", "version": "1.0.0"}


@app.on_event("startup")
async def startup():
    """Log Redis connection on startup."""
    redis_url = os.getenv("REDIS_URL", "not set")
    # Redact password for security
    safe_url = re.sub(r'://[^:]+:[^@]+@', '://***:***@', redis_url)
    print(f"🔧 REDIS_URL: {safe_url}")
    logger.info(f"REDIS_URL: {safe_url}")
    
    # Test Celery connection
    try:
        from app.core.celery_app import celery_app
        # Try to inspect active tasks (this will fail if Redis is not connected)
        inspect = celery_app.control.inspect()
        active = inspect.active()
        if active is not None:
            logger.info("✅ Celery connected to Redis successfully")
        else:
            logger.warning("⚠️ Celery could not connect to Redis - tasks may not execute")
    except Exception as e:
        logger.warning(f"⚠️ Celery connection check failed: {e}")


@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

