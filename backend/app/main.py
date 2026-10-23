
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.health import router as health_router
from app.api.routes.analysis import router as analysis_router
from app.api.routes.exports import router as exports_router
from app.core.config import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Shared HTTP clients and caches can be initialized here later.
    yield
    # Shared resources will be closed here later.


settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    description=(
        "Historical analysis of Great Britain wind generation "
        "forecast accuracy using Elexon BMRS data."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "OPTIONS"],
    allow_headers=["*"],
)

app.include_router(health_router, prefix="/api")
app.include_router(analysis_router, prefix="/api")
app.include_router(exports_router, prefix="/api")


@app.get("/")
def root() -> dict[str, str]:
    return {
        "service": settings.app_name,
        "docs": "/docs",
        "health": "/api/health",
    }
