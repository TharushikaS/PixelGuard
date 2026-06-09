"""PixelGuard FastAPI application entry point."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.database import close_mongo_connection, connect_to_mongo
from app.routes import decode_router, encode_router, tracking_router

logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("pixelguard")


@asynccontextmanager
async def lifespan(app: FastAPI):  # noqa: ARG001
    """Open/close the MongoDB client around the app's life."""
    try:
        await connect_to_mongo()
    except Exception as exc:  # noqa: BLE001
        # Don't crash the server in dev when Mongo is down — log loudly.
        logger.error("MongoDB unavailable at startup: %s", exc)
    yield
    await close_mongo_connection()


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    debug=settings.DEBUG,
    lifespan=lifespan,
)

# CORS: explicit origins from settings, plus a regex catch-all for
# any localhost / 127.0.0.1 port when DEBUG=True. Prod stays strict.
_cors_kwargs = {
    "allow_origins": settings.ALLOWED_ORIGINS,
    "allow_credentials": True,
    "allow_methods": ["*"],
    "allow_headers": ["*"],
}
if settings.DEBUG:
    _cors_kwargs["allow_origin_regex"] = r"https?://(localhost|127\.0\.0\.1)(:\d+)?"

app.add_middleware(CORSMiddleware, **_cors_kwargs)


# ---------------------------------------------------------------------------
# Meta endpoints
# ---------------------------------------------------------------------------
@app.get("/health", tags=["meta"])
async def health_check():
    """Liveness probe."""
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
    }


@app.get("/", tags=["meta"])
async def root():
    return {
        "message": f"Welcome to {settings.APP_NAME}",
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "redoc": "/redoc",
    }


# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
app.include_router(encode_router)
app.include_router(decode_router)
app.include_router(tracking_router)


# ---------------------------------------------------------------------------
# Error handlers
# ---------------------------------------------------------------------------
@app.exception_handler(Exception)
async def general_exception_handler(request, exc):  # noqa: ARG001
    logger.exception("Unhandled error")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
    )
