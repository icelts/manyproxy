from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import time
import logging
import os
import uuid
from logging.handlers import RotatingFileHandler
from pathlib import Path

from app.core.config import settings
from app.core.database import AsyncSessionLocal, engine
from app.api.v1.api import api_router
from app.api.v1.public_api import public_router
from app.services.session_service import SessionService
from app.services.proxy_service import ProxyService
from app.utils.cache import RateLimiter, init_redis

api_rate_limiter = RateLimiter()
API_KEY_REQUIRED_PREFIXES = [
    "/api/v1/proxy",
]

# Logging
# Configure logging (console + rotating file)
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

log_dir = Path("logs")
log_dir.mkdir(parents=True, exist_ok=True)
log_file = log_dir / "app.log"

file_handler = RotatingFileHandler(log_file, maxBytes=2 * 1024 * 1024, backupCount=5)
file_handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
file_handler.setLevel(logging.INFO)
logger.addHandler(file_handler)
root_logger = logging.getLogger()
root_logger.addHandler(file_handler)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """App lifecycle management."""
    logger.info("Starting up...")

    # Initialize Redis (non-fatal if unavailable)
    await init_redis()

    # IMPORTANT: Do NOT create tables at runtime in production to avoid drift.
    # Database schema should be managed exclusively by Alembic migrations.
    # If you really need runtime create_all (e.g., local dev), enable via env setting.
    if settings.ALLOW_DB_CREATE_ALL:
        try:
            from app.core.database import Base  # lazy import to avoid cycle

            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            logger.info("Database tables ensured (create_all).")
        except Exception as e:
            logger.error(f"create_all failed: {e}")

    yield

    logger.info("Shutting down...")


# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    description="Proxy Platform API: IP更换接口服务",
    openapi_url="/api/v1/openapi.json" if settings.DEBUG else None,
    docs_url="/api/v1/docs" if settings.DEBUG else None,
    redoc_url="/api/v1/redoc" if settings.DEBUG else None,
    lifespan=lifespan,
)

# Create public API app for customer documentation (always enabled)
public_app = FastAPI(
    title="IP更换接口服务",
    version="1.0.0",
    description="提供代理IP更换服务的API接口 - 客户专用文档",
    openapi_url="/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Add middleware to public app
public_app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

public_app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=getattr(settings, "ALLOWED_HOSTS", ["*"]),
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Trusted hosts (restrict in production via ALLOWED_HOSTS)
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=getattr(settings, "ALLOWED_HOSTS", ["*"]),
)


# Request logging middleware (runs first - defined last)
@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    """Log each incoming request with timing information."""
    request_id = uuid.uuid4().hex[:8]
    request.state.request_id = request_id
    start = time.time()
    logger.info("[%s] %s %s - received", request_id, request.method, request.url.path)

    try:
        response = await call_next(request)
    except Exception as exc:
        logger.exception("[%s] %s %s - unhandled exception: %s", request_id, request.method, request.url.path, exc)
        raise

    duration_ms = int((time.time() - start) * 1000)
    logger.info("[%s] %s %s - completed with %s in %sms", request_id, request.method, request.url.path, response.status_code, duration_ms)
    return response


# API key auth middleware (runs second - defined first)
@app.middleware("http")
async def api_key_auth_middleware(request: Request, call_next):
    """API key auth and rate limit middleware."""
    request_id = getattr(request.state, "request_id", "N/A")
    path = request.url.path
    
    # Skip auth for these exact paths and prefixes
    skip_auth_patterns = [
        "/api/v1/session/login",
        "/api/v1/session/register",
        "/docs",
        "/redoc",
        "/openapi.json",
        "/health",
        "/",
        "/frontend/",
        "/css/",
        "/js/",
        "/pages/",
        "/public/docs",
        "/public/redoc",
        "/public/openapi.json",
        "/public/info",
    ]

    # Check if path matches any skip pattern (exact match or prefix match)
    should_skip = False
    for pattern in skip_auth_patterns:
        if pattern == '/':
            # Special case: root path should only match exactly
            if path == pattern:
                should_skip = True
                break
        elif pattern.endswith('/'):
            # Directory prefix match
            if path.startswith(pattern):
                should_skip = True
                break
        else:
            # Exact match
            if path == pattern:
                should_skip = True
                break

    if should_skip:
        logger.debug("[%s] %s skipped auth (public path)", request_id, path)
        return await call_next(request)

    # Only enforce auth under specific prefixes
    if not any(path.startswith(prefix) for prefix in API_KEY_REQUIRED_PREFIXES):
        logger.debug("[%s] %s not in protected prefixes, skipping API key check", request_id, path)
        return await call_next(request)

    api_key_info = None
    user = None
    auth_type = None
    api_key = request.headers.get("X-API-Key")

    # 仅使用API Key认证，不再支持JWT认证
    if api_key:
        # API key认证
        logger.debug("[%s] %s attempting API key authentication with key: %s", request_id, path, api_key[:10] + "...")
        async with AsyncSessionLocal() as db:
            api_key_info = await SessionService.get_api_key_info(db, api_key)
            if not api_key_info:
                logger.warning("[%s] %s invalid API key: %s", request_id, path, api_key)
                return JSONResponse(status_code=401, content={"detail": "Invalid API key"})
            user = await SessionService.get_user_by_id(db, api_key_info["user_id"])
            if not user or not user.is_active:
                logger.warning("[%s] %s API key user inactive or missing (user_id=%s)", request_id, path, api_key_info["user_id"])
                return JSONResponse(
                    status_code=403, content={"detail": "User is inactive or not found"}
                )
        rate_limit = api_key_info.get("rate_limit") or settings.DEFAULT_RATE_LIMIT
        if not await api_rate_limiter.is_allowed(api_key, max_requests=rate_limit):
            logger.warning("[%s] %s API key %s exceeded rate limit (%s req/min)", request_id, path, api_key, rate_limit)
            return JSONResponse(status_code=429, content={"detail": "Rate limit exceeded"})
        auth_type = "api_key"
        logger.info("[%s] %s API key authentication successful for user_id=%s", request_id, path, user.id)
    else:
        # 没有API Key，认证失败
        logger.warning("[%s] %s missing API key for protected endpoint", request_id, path)
        return JSONResponse(status_code=401, content={"detail": "API key required"})

    request.state.user = user
    request.state.user_id = user.id
    request.state.api_key_id = api_key_info["api_key_id"] if api_key_info else None
    request.state.auth_type = auth_type
    logger.debug("[%s] %s authenticated via %s (user_id=%s)", request_id, path, auth_type, user.id)

    start_time = time.time()
    response = await call_next(request)
    process_time = int((time.time() - start_time) * 1000)

    if api_key_info:
        # Record API usage (best-effort)
        try:
            async with AsyncSessionLocal() as db:
                await ProxyService.record_api_usage(
                    db=db,
                    user_id=api_key_info["user_id"],
                    api_key_id=api_key_info["api_key_id"],
                    endpoint=str(request.url.path),
                    method=request.method,
                    status_code=response.status_code,
                    response_time=process_time,
                    ip_address=request.client.host if request.client else None,
                    user_agent=request.headers.get("user-agent", ""),
                )
        except Exception as e:
            logger.error("[%s] Failed to record API usage: %s", request_id, e)

    response.headers["X-Process-Time"] = str(process_time)
    return response


# Exception handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """HTTP exception handler."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "status_code": exc.status_code},
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """General exception handler."""
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


@app.get("/health")
async def health_check():
    """Health check."""
    return {"status": "healthy", "version": settings.VERSION, "timestamp": time.time()}


@app.get("/")
async def root():
    """Root endpoint - returns the homepage."""
    from fastapi.responses import FileResponse
    import os
    
    homepage_path = "frontend/index.html"
    if os.path.exists(homepage_path):
        return FileResponse(homepage_path)
    else:
        return {"message": "Proxy Platform API", "version": settings.VERSION}


# Static files
if os.path.exists("frontend"):
    app.mount("/frontend", StaticFiles(directory="frontend"), name="frontend")
    app.mount("/css", StaticFiles(directory="frontend/css"), name="css")
    app.mount("/js", StaticFiles(directory="frontend/js"), name="js")
    app.mount("/pages", StaticFiles(directory="frontend/pages"), name="pages")
    app.mount("/components", StaticFiles(directory="frontend/components"), name="components")

# Include API routes
app.include_router(api_router)

# Include public API routes in the public app
public_app.include_router(public_router)

# Mount public app as a sub-application
app.mount("/public", public_app)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level="info",
    )
