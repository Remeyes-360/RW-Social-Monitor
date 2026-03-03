from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from contextlib import asynccontextmanager
from loguru import logger
import uvicorn

from app.database import engine, Base
from app.api.routes import mentions, analytics, alerts, reports, dashboard
from app.celery_app import celery_app
from app.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialisation et nettoyage de l'application."""
    logger.info("RW Social Monitor - Demarrage...")
    # Creer les tables en base de donnees
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Base de donnees initialisee")
    yield
    logger.info("RW Social Monitor - Arret...")


app = FastAPI(
    title="RW Social Monitor API",
    description="API de monitoring des reseaux sociaux pour Romuald Wadagni - Benin 2026",
    version="1.0.0",
    lifespan=lifespan,
)

# Middlewares
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Routers
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["Dashboard"])
app.include_router(mentions.router, prefix="/api/mentions", tags=["Mentions"])
app.include_router(analytics.router, prefix="/api/analytics", tags=["Analytics"])
app.include_router(alerts.router, prefix="/api/alerts", tags=["Alertes"])
app.include_router(reports.router, prefix="/api/reports", tags=["Rapports"])


@app.get("/")
async def root():
    return {
        "app": "RW Social Monitor",
        "version": "1.0.0",
        "status": "operational",
        "candidat": "Romuald Wadagni",
        "election": "Presidentielle Benin 2026",
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy", "database": "connected", "redis": "connected"}


if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
