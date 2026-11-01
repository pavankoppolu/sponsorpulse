"""FastAPI application entry point for SponsorPulse."""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import init_db
from app.api.routes import discovery, enrichment, outreach, kanban, auth_gmail


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle."""
    init_db()
    yield


app = FastAPI(
    title="SponsorPulse",
    description="Industry & Corporate Engagement outreach management platform",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(discovery.router, prefix="/api/discovery", tags=["Discovery"])
app.include_router(enrichment.router, prefix="/api/enrichment", tags=["Enrichment"])
app.include_router(outreach.router, prefix="/api/outreach", tags=["Outreach"])
app.include_router(kanban.router, prefix="/api/kanban", tags=["Kanban"])
app.include_router(auth_gmail.router, prefix="/api/auth", tags=["Gmail Auth"])


@app.get("/api/health")
async def health_check():
    return {"status": "ok", "service": "SponsorPulse"}

