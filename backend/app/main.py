"""
VeriSpire AI — Backend Entry Point

Wires together every router, CORS, static file serving for uploads,
auto-seeds verification agents in development, and exposes Swagger at /docs.
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
from app.models import *  # noqa: F401,F403 — populate metadata for create_all

app = FastAPI(
    title=settings.APP_NAME,
    description=(
        "VeriSpire AI — Multi-Agent Reasoning & Verification Engine. "
        "Planner, generator, subprocess sandbox, and independent verifier "
        "produce self-correcting audit trails (HackFusion Theme 8)."
    ),
    version="2.0.0",
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
        "version": "2.0.0",
        "status": "running",
        "docs": "/docs",
        "engine": "OrchestratorEngine (planner → generator → sandbox → verifier)",
    }


@app.get("/health", tags=["Root"])
def health():
    return {"status": "ok"}


@app.on_event("startup")
def on_startup():
    if settings.APP_ENV == "development":
        Base.metadata.create_all(bind=engine)
        from app.seed import run as seed_agents

        seed_agents()
