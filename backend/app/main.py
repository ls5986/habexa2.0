from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from app.core.config import settings
from app.api.v1 import deals, analysis, suppliers, notifications, settings as api_settings, watchlist, orders, billing, telegram, amazon, keepa
import logging

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Habexa API",
    description="Amazon Sourcing Intelligence Platform API",
    version="1.0.0"
)

# CORS - MUST be added before other middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.FRONTEND_URL,
        "http://localhost:5173",
        "http://localhost:5189",  # Vite may use different ports
        "http://localhost:3000",
        "*",  # Allow all origins in development (remove in production)
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
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
        headers={
            "Access-Control-Allow-Origin": request.headers.get("origin", "*"),
            "Access-Control-Allow-Credentials": "true",
        }
    )

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Ensure CORS headers are set on HTTP exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers={
            "Access-Control-Allow-Origin": request.headers.get("origin", "*"),
            "Access-Control-Allow-Credentials": "true",
        }
    )

# Include routers
app.include_router(deals.router, prefix=f"{settings.API_V1_PREFIX}/deals", tags=["deals"])
app.include_router(analysis.router, prefix=f"{settings.API_V1_PREFIX}/analyze", tags=["analysis"])
app.include_router(suppliers.router, prefix=f"{settings.API_V1_PREFIX}/suppliers", tags=["suppliers"])
app.include_router(notifications.router, prefix=f"{settings.API_V1_PREFIX}/notifications", tags=["notifications"])
app.include_router(api_settings.router, prefix=f"{settings.API_V1_PREFIX}/settings", tags=["settings"])
app.include_router(watchlist.router, prefix=f"{settings.API_V1_PREFIX}/watchlist", tags=["watchlist"])
app.include_router(orders.router, prefix=f"{settings.API_V1_PREFIX}/orders", tags=["orders"])
app.include_router(billing.router, prefix=f"{settings.API_V1_PREFIX}/billing", tags=["billing"])
app.include_router(telegram.router, prefix=f"{settings.API_V1_PREFIX}/integrations/telegram", tags=["telegram"])
app.include_router(amazon.router, prefix=f"{settings.API_V1_PREFIX}", tags=["amazon"])
app.include_router(keepa.router, prefix=f"{settings.API_V1_PREFIX}", tags=["keepa"])


@app.get("/")
async def root():
    return {"message": "Habexa API", "version": "1.0.0"}


@app.get("/health")
async def health():
    return {"status": "healthy"}

