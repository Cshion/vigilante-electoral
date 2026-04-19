"""FastAPI main application."""
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Response, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi_cache import FastAPICache
from fastapi_cache.backends.inmemory import InMemoryBackend
from starlette.middleware.base import BaseHTTPMiddleware
from datetime import datetime

from .config import settings
from .routers import results_router
from .routers.positions import router as positions_router
from .routers.scrape import router as scrape_router
from .routers.notifications import router as notifications_router
from .database import db


class IgnoreClientCacheMiddleware(BaseHTTPMiddleware):
    """
    Middleware that removes client Cache-Control headers.
    This ensures our server-side cache always works, regardless of
    browser hard-refresh or DevTools "Disable cache" setting.
    """
    async def dispatch(self, request: Request, call_next):
        # Remove cache-control header from incoming request
        if "cache-control" in request.headers:
            # Create mutable headers copy without cache-control
            mutable_headers = dict(request.headers)
            mutable_headers.pop("cache-control", None)
            # We can't modify request.headers directly, but fastapi-cache
            # checks request.headers.get("cache-control"), so we need a workaround
            request.scope["headers"] = [
                (k.encode(), v.encode()) for k, v in mutable_headers.items()
                if k.lower() != "cache-control"
            ]
        return await call_next(request)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup and shutdown events."""
    # Startup: Initialize cache
    FastAPICache.init(InMemoryBackend())
    yield
    # Shutdown: nothing to clean up for in-memory cache


# Disable docs in production
docs_url = "/docs" if settings.DEBUG else None
redoc_url = "/redoc" if settings.DEBUG else None

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Backend API for monitoring Peruvian electoral results from ONPE",
    debug=settings.DEBUG,
    docs_url=docs_url,
    redoc_url=redoc_url,
    openapi_url="/openapi.json" if settings.DEBUG else None,
    lifespan=lifespan,
)

# CORS Configuration - only from environment variables
# Parse origins from ALLOWED_ORIGINS env var (comma-separated)
_origins = [o.strip() for o in settings.ALLOWED_ORIGINS.split(",") if o.strip()]
_allow_all = "*" in _origins or settings.ALLOWED_ORIGINS == "*"

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if _allow_all else _origins,
    allow_origin_regex=settings.CORS_ORIGIN_REGEX or None,
    allow_credentials=not _allow_all,  # Can't use credentials with "*"
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ignore client Cache-Control headers so our server cache always works
# (prevents browser hard-refresh or DevTools from bypassing server cache)
app.add_middleware(IgnoreClientCacheMiddleware)

# Include routers
app.include_router(results_router)
app.include_router(positions_router)
app.include_router(scrape_router)  # POST /api/scrape + GET /api/scrape/status
app.include_router(notifications_router)  # GET /api/notifications


@app.get("/health")
async def health_check(response: Response):
    """Health check endpoint."""
    # Never cache health checks
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    
    if not db.is_connected:
        return {"status": "degraded"}
    return {"status": "healthy"}


@app.get("/")
async def root(response: Response):
    """Root endpoint with API info."""
    # Static info - cache for 1 hour
    response.headers["Cache-Control"] = "public, max-age=3600, s-maxage=3600"
    
    return {
        "name": "Vigilante Electoral API",
        "status": "running"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
