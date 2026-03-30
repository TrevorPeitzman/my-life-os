"""Life OS — FastAPI application entrypoint."""
from __future__ import annotations

import logging
import secrets

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.models import HealthResponse
from app.routers import ai, calendar, daily, journal, planning, push, tasks
from app.services import gcal_service

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Life OS",
    version="1.0.0",
    docs_url=None,   # Disable Swagger UI in production
    redoc_url=None,
)

# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)

# ---------------------------------------------------------------------------
# Exception handlers
# ---------------------------------------------------------------------------

@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
    return JSONResponse(status_code=422, content={"detail": str(exc)})


# ---------------------------------------------------------------------------
# Auth dependency
# ---------------------------------------------------------------------------

def verify_api_key(request: Request) -> None:
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
    provided = auth_header[7:]  # strip "Bearer "
    # Pad to equal length to prevent secrets.compare_digest length leak
    # (both sides must be the same type and we compare against a fixed-length key)
    if not secrets.compare_digest(provided.encode(), settings.API_KEY.encode()):
        raise HTTPException(status_code=401, detail="Invalid API key")


# ---------------------------------------------------------------------------
# Unauthenticated endpoints
# ---------------------------------------------------------------------------

@app.get("/health", response_model=HealthResponse, tags=["meta"])
def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        vault_dir=str(settings.VAULT_DIR),
        tz=settings.TZ,
        ai_provider=settings.AI_PROVIDER,
        gcal_connected=gcal_service.is_connected(),
    )


@app.get("/config/public", tags=["meta"])
def public_config() -> dict:
    """Return public (non-secret) configuration needed by the frontend."""
    return {
        "vapid_public_key": settings.VAPID_PUBLIC_KEY or "",
        "ai_provider": settings.AI_PROVIDER,
        "gcal_configured": gcal_service.is_configured(),
    }


# ---------------------------------------------------------------------------
# Authenticated routers
# ---------------------------------------------------------------------------

_auth = [Depends(verify_api_key)]

app.include_router(daily.router, dependencies=_auth)
app.include_router(journal.router, dependencies=_auth)
app.include_router(tasks.router, dependencies=_auth)
app.include_router(push.router, dependencies=_auth)
app.include_router(ai.router, dependencies=_auth)
app.include_router(calendar.router, dependencies=_auth)
app.include_router(planning.router, dependencies=_auth)


# ---------------------------------------------------------------------------
# Startup log
# ---------------------------------------------------------------------------

@app.on_event("startup")
async def on_startup() -> None:
    logger.info(
        "Life OS started | TZ=%s | AI=%s | GCal=%s | Vault=%s",
        settings.TZ,
        settings.AI_PROVIDER,
        "connected" if gcal_service.is_connected() else "not connected",
        settings.VAULT_DIR,
    )
