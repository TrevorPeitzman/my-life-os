"""Life OS — FastAPI application entrypoint (Cloudflare Tunnel variant).

Differences from the nginx variant:
- All API endpoints are served under /api/ (nginx variant had nginx strip
  the prefix; here FastAPI does it natively).
- Frontend static files are served directly by FastAPI (StaticFiles mount)
  so a single cloudflared → backend connection handles everything.
- sw.js is served with Service-Worker-Allowed and no-cache headers.
- No TLS config here — Cloudflare Tunnel handles TLS at the edge.
"""
from __future__ import annotations

import logging
import os
import secrets
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.models import HealthResponse
from app.routers import ai, calendar, daily, journal, milestones, planning, push, tasks
from app.services import gcal_service

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)

# Frontend directory — mounted as a volume from the host
FRONTEND_DIR = Path(os.getenv("FRONTEND_DIR", "/app/frontend"))

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Life OS",
    version="1.0.0",
    docs_url=None,
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
    provided = auth_header[7:]
    if not secrets.compare_digest(provided.encode(), settings.API_KEY.encode()):
        raise HTTPException(status_code=401, detail="Invalid API key")

# ---------------------------------------------------------------------------
# Unauthenticated endpoints (no /api prefix needed for health check tooling,
# but /api/ prefix is kept for consistency with the frontend)
# ---------------------------------------------------------------------------

@app.get("/api/health", response_model=HealthResponse, tags=["meta"])
def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        vault_dir=str(settings.VAULT_DIR),
        tz=settings.TZ,
        ai_provider=settings.AI_PROVIDER,
        gcal_connected=gcal_service.is_connected(),
    )


@app.get("/api/config/public", tags=["meta"])
def public_config() -> dict:
    return {
        "vapid_public_key": settings.VAPID_PUBLIC_KEY or "",
        "ai_provider": settings.AI_PROVIDER,
        "gcal_configured": gcal_service.is_configured(),
    }

# ---------------------------------------------------------------------------
# Authenticated routers — all under /api/
# ---------------------------------------------------------------------------

_auth = [Depends(verify_api_key)]
_api = "/api"

app.include_router(daily.router,       prefix=_api, dependencies=_auth)
app.include_router(journal.router,     prefix=_api, dependencies=_auth)
app.include_router(tasks.router,       prefix=_api, dependencies=_auth)
app.include_router(push.router,        prefix=_api, dependencies=_auth)
app.include_router(ai.router,          prefix=_api, dependencies=_auth)
app.include_router(calendar.router,    prefix=_api, dependencies=_auth)
app.include_router(planning.router,    prefix=_api, dependencies=_auth)
app.include_router(milestones.router,  prefix=_api, dependencies=_auth)

# ---------------------------------------------------------------------------
# Static file serving
# NOTE: These routes must be defined AFTER all API routes so they don't
# shadow the /api/ paths.
# ---------------------------------------------------------------------------

@app.get("/sw.js", include_in_schema=False)
def service_worker() -> FileResponse:
    """Serve the service worker with required headers."""
    return FileResponse(
        str(FRONTEND_DIR / "sw.js"),
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Service-Worker-Allowed": "/",
            "Content-Type": "application/javascript",
        },
    )


@app.get("/manifest.json", include_in_schema=False)
def manifest() -> FileResponse:
    return FileResponse(
        str(FRONTEND_DIR / "manifest.json"),
        headers={
            "Cache-Control": "no-cache",
            "Content-Type": "application/manifest+json",
        },
    )


# Mount remaining static files (HTML, CSS, JS, images) at root.
# html=True means index.html is served for directory requests and unknown
# paths (SPA-style routing).
if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="static")
else:
    logger.warning("FRONTEND_DIR %s does not exist — static files will not be served", FRONTEND_DIR)

# ---------------------------------------------------------------------------
# Startup log
# ---------------------------------------------------------------------------

@app.on_event("startup")
async def on_startup() -> None:
    logger.info(
        "Life OS (Cloudflare Tunnel mode) | TZ=%s | AI=%s | GCal=%s | Vault=%s | Frontend=%s",
        settings.TZ,
        settings.AI_PROVIDER,
        "connected" if gcal_service.is_connected() else "not connected",
        settings.VAULT_DIR,
        FRONTEND_DIR,
    )
