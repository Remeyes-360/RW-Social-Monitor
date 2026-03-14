from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from loguru import logger
import uvicorn

from app.database import engine, Base, AsyncSessionLocal
from app.api.routes import mentions, dashboard
from app.config import settings

# Lazy import to avoid circular during startup
try:
    from app.api.routes import analytics, alerts, reports
    _extra_routes = True
except ImportError:
    _extra_routes = False


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialisation et nettoyage de l'application."""
    logger.info("RW Social Monitor - Demarrage...")
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

# FIX: Restricted CORS — credentials=True with wildcard methods/headers is overly permissive
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type", "Accept"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Routers
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["Dashboard"])
app.include_router(mentions.router, prefix="/api/mentions", tags=["Mentions"])
if _extra_routes:
    app.include_router(analytics.router, prefix="/api/analytics", tags=["Analytics"])
    app.include_router(alerts.router, prefix="/api/alerts", tags=["Alertes"])
    app.include_router(reports.router, prefix="/api/reports", tags=["Rapports"])


@app.get("/")
async def root():
    return {
        "app": "RW Social Monitor",
        "version": "1.0.0",
        "status": "operational",
    }


@app.get("/health")
async def health_check():
    """FIX: Actually probe DB and Redis instead of returning hardcoded 'connected'."""
    health = {"status": "healthy", "database": "unknown", "redis": "unknown"}
    errors = []

    # Probe database
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(__import__("sqlalchemy").text("SELECT 1"))
        health["database"] = "connected"
    except Exception as e:
        health["database"] = "error"
        errors.append(f"database: {e}")

    # Probe Redis
    try:
        import redis.asyncio as aioredis
        r = aioredis.from_url(settings.REDIS_URL, socket_connect_timeout=2)
        await r.ping()
        await r.aclose()
        health["redis"] = "connected"
    except Exception as e:
        health["redis"] = "error"
        errors.append(f"redis: {e}")

    if errors:
        health["status"] = "degraded"
        health["errors"] = errors
        return JSONResponse(status_code=503, content=health)

    return health


if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
