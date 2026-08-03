"""
VICTORUS AI — Backend Entry Point (Version 1)

Wires together every router, CORS, static file serving for uploads,
and exposes interactive Swagger docs at /docs.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.api.v1 import memory

from app.api.v1 import (
    agents,
    api_keys,
    auth,
    conversations,
    dashboard,
    files,
    integrations,
    notifications,
    onboarding,
    profile,
    security_routes,
    settings_routes,
    tasks,
)
from app.core.config import settings
from app.db.base_class import Base
from app.db.session import engine

app = FastAPI(
    title=settings.APP_NAME,
    description=(
        "VICTORUS AI Workforce Platform — Version 1 API. "
        "AI responses are currently a placeholder (see app/services/ai_service.py); "
        "Version 2 plugs a real model into that single file."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve uploaded files (resumes, avatars, general uploads) statically.
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")

API_PREFIX = settings.API_V1_PREFIX
app.include_router(auth.router, prefix=API_PREFIX)
app.include_router(onboarding.router, prefix=API_PREFIX)
app.include_router(profile.router, prefix=API_PREFIX)
app.include_router(files.router, prefix=API_PREFIX)
app.include_router(notifications.router, prefix=API_PREFIX)
app.include_router(conversations.router, prefix=API_PREFIX)
app.include_router(agents.router, prefix=API_PREFIX)
app.include_router(tasks.router, prefix=API_PREFIX)
app.include_router(dashboard.router, prefix=API_PREFIX)
app.include_router(settings_routes.router, prefix=API_PREFIX)
app.include_router(security_routes.router, prefix=API_PREFIX)
app.include_router(api_keys.router, prefix=API_PREFIX)
app.include_router(integrations.router, prefix=API_PREFIX)
app.include_router(memory.router, prefix=API_PREFIX)


@app.get("/", tags=["Root"])
def root():
    return {
        "app": settings.APP_NAME,
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
        "note": "AI integration is a dummy stub in Version 1. See app/services/ai_service.py.",
    }


@app.get("/health", tags=["Root"])
def health():
    return {"status": "ok"}


@app.on_event("startup")
def on_startup():
    # Dev convenience: auto-create tables if they don't exist yet.
    # In production, rely on Alembic migrations instead (see alembic/).
    if settings.APP_ENV == "development":
        Base.metadata.create_all(bind=engine)
