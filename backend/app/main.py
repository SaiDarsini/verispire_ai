"""
VeriSpire AI — Backend Entry Point

Wires together every router, CORS, static file serving for uploads,
auto-seeds verification agents in development, and exposes Swagger at /docs.
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# 1. Database models & Base
from app.db.base_class import Base
from app.db.session import engine
import app.models  # Imports model registry safely without overriding router symbols

# 2. API Routers from app.api.v1
from app.api.v1 import (
    agents,
    api_keys,
    auth,
    conversations,
    dashboard,
    files,
    integrations,
    memory,
    notifications,
    onboarding,
    profile as profile_router,
    security_routes,
    settings_routes,
    tasks,
)
from app.core.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Handles application startup and shutdown events cleanly.
    Creates database tables and seeds default verification agents in development.
    """
    if getattr(settings, "APP_ENV", "development") == "development":
        Base.metadata.create_all(bind=engine)
        try:
            from app.seed import run as seed_agents

            seed_agents()
            print("[VeriSpire] Verification agents successfully initialized/verified.")
        except Exception as e:
            print(f"[Startup Warning] Agent seeding skipped or encountered note: {e}")
    yield


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
    lifespan=lifespan,
)

# Explicitly permit local origins across both port 5500 and standard development ports
allowed_origins = [
    "http://localhost:5500",
    "http://127.0.0.1:5500",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]

if hasattr(settings, "cors_origins_list") and settings.cors_origins_list:
    for origin in settings.cors_origins_list:
        if origin not in allowed_origins:
            allowed_origins.append(origin)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve uploaded files statically
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")

# Mount API routers under versioned prefix
API_PREFIX = settings.API_V1_PREFIX
app.include_router(auth.router, prefix=API_PREFIX)
app.include_router(onboarding.router, prefix=API_PREFIX)
app.include_router(profile_router.router, prefix=API_PREFIX)
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