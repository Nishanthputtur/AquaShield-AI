"""
FastAPI application entrypoint for AquaShield AI.
"""

from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.config.settings import settings
from backend.app.routes.auth import router as auth_router
from backend.app.routes.users import router as users_router
from backend.app.services.simulation_service import simulation_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("aquashield")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context manager."""
    logger.info("starting")
    await simulation_service._force_stopped()
    yield
    await simulation_service._cancel_task()


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan,
)

# CORS middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH", "*"],
    allow_headers=["Authorization", "Content-Type", "Accept", "*"],
)

# Mount API routers
app.include_router(auth_router)
app.include_router(users_router)


@app.get("/health")
def health():
    """Service health check endpoint."""
    return {"status": "ok"}
