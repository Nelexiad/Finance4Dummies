from typing import Literal

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import text

from app.core.config import get_settings
from app.core.database import AsyncSessionLocal
from app.core.redis import get_redis_client

router = APIRouter(prefix="/health", tags=["Health"])


class HealthResponse(BaseModel):
    status: Literal["ok"]
    app: str
    environment: str


class DependencyHealth(BaseModel):
    database: Literal["ok", "error"]
    redis: Literal["ok", "error"]


class ReadinessResponse(BaseModel):
    status: Literal["ok", "degraded"]
    dependencies: DependencyHealth


@router.get("", response_model=HealthResponse, summary="Liveness check")
async def liveness() -> HealthResponse:
    settings = get_settings()
    return HealthResponse(
        status="ok",
        app=settings.app_name,
        environment=settings.app_env,
    )


@router.get(
    "/ready",
    response_model=ReadinessResponse,
    summary="Readiness check (PostgreSQL + Redis)",
)
async def readiness() -> JSONResponse:
    db_status: Literal["ok", "error"] = "ok"
    redis_status: Literal["ok", "error"] = "ok"

    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
    except Exception:
        db_status = "error"

    try:
        redis_client = get_redis_client()
        await redis_client.ping()
    except Exception:
        redis_status = "error"

    overall: Literal["ok", "degraded"] = (
        "ok" if db_status == "ok" and redis_status == "ok" else "degraded"
    )
    payload = ReadinessResponse(
        status=overall,
        dependencies=DependencyHealth(database=db_status, redis=redis_status),
    )
    http_status = status.HTTP_200_OK if overall == "ok" else status.HTTP_503_SERVICE_UNAVAILABLE
    return JSONResponse(status_code=http_status, content=payload.model_dump())
