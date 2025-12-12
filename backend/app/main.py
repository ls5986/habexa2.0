from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from app.core.config import settings
from app.api.v1 import deals, analysis, suppliers, notifications, settings as api_settings, watchlist, orders, billing, telegram, amazon, keepa, debug, market, sp_api, products, brands, jobs, batch, buy_list, buy_lists, supplier_orders, tpl, fba_shipments, financial, templates, prep_centers, auth, users, upload, favorites, products_bulk, product_sources, pack_variants, brand_restrictions
from app.routers import analyzer
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
# Production frontend URL
PRODUCTION_FRONTEND_URL = "https://habexa-frontend.onrender.com"
PRODUCTION_FRONTEND_URL_ALT = "https://habexa.onrender.com"  # Alternative domain

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.FRONTEND_URL,
        PRODUCTION_FRONTEND_URL,
        PRODUCTION_FRONTEND_URL_ALT,
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
        PRODUCTION_FRONTEND_URL,
        PRODUCTION_FRONTEND_URL_ALT,
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
        PRODUCTION_FRONTEND_URL,
        PRODUCTION_FRONTEND_URL_ALT,
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
app.include_router(products_bulk.router, prefix=f"{settings.API_V1_PREFIX}", tags=["products"])
app.include_router(product_sources.router, prefix=f"{settings.API_V1_PREFIX}", tags=["product-sources"])
app.include_router(brands.router, prefix=f"{settings.API_V1_PREFIX}", tags=["brands"])
app.include_router(jobs.router, prefix=f"{settings.API_V1_PREFIX}", tags=["jobs"])
app.include_router(batch.router, prefix=f"{settings.API_V1_PREFIX}", tags=["batch"])
app.include_router(analysis.router, prefix=f"{settings.API_V1_PREFIX}/analyze", tags=["analysis"])
app.include_router(suppliers.router, prefix=f"{settings.API_V1_PREFIX}/suppliers", tags=["suppliers"])
app.include_router(notifications.router, prefix=f"{settings.API_V1_PREFIX}/notifications", tags=["notifications"])
app.include_router(api_settings.router, prefix=f"{settings.API_V1_PREFIX}/settings", tags=["settings"])
app.include_router(watchlist.router, prefix=f"{settings.API_V1_PREFIX}/watchlist", tags=["watchlist"])
app.include_router(buy_list.router, prefix=f"{settings.API_V1_PREFIX}/buy-list", tags=["buy-list"])
app.include_router(buy_lists.router, prefix=f"{settings.API_V1_PREFIX}", tags=["buy-lists"])
app.include_router(supplier_orders.router, prefix=f"{settings.API_V1_PREFIX}", tags=["supplier-orders"])
app.include_router(tpl.router, prefix=f"{settings.API_V1_PREFIX}", tags=["tpl"])
app.include_router(fba_shipments.router, prefix=f"{settings.API_V1_PREFIX}", tags=["fba-shipments"])
app.include_router(financial.router, prefix=f"{settings.API_V1_PREFIX}", tags=["financial"])
app.include_router(templates.router, prefix=f"{settings.API_V1_PREFIX}", tags=["templates"])
app.include_router(prep_centers.router, prefix=f"{settings.API_V1_PREFIX}", tags=["prep-centers"])
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
app.include_router(analyzer.router, prefix=f"{settings.API_V1_PREFIX}", tags=["analyzer"])
app.include_router(pack_variants.router, prefix=f"{settings.API_V1_PREFIX}", tags=["pack-variants"])
app.include_router(brand_restrictions.router, prefix=f"{settings.API_V1_PREFIX}", tags=["brand-restrictions"])


@app.get("/")
async def root():
    return {"message": "Habexa API", "version": "1.0.0"}


@app.on_event("startup")
async def startup():
    """Run on application startup."""
    logger.info("Starting Habexa backend...")
    
    # Log Redis connection
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
    
    # Start background job scheduler
    try:
        from app.core.scheduler import start_scheduler
        start_scheduler()
    except Exception as e:
        logger.error(f"Failed to start scheduler: {e}", exc_info=True)
    
    logger.info("✅ Application started successfully")


@app.on_event("shutdown")
async def shutdown():
    """Run on application shutdown."""
    logger.info("Shutting down Habexa backend...")
    try:
        from app.core.scheduler import stop_scheduler
        stop_scheduler()
    except Exception as e:
        logger.error(f"Error stopping scheduler: {e}")
    logger.info("✅ Application stopped")


@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

