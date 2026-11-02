from __future__ import annotations

import structlog
from fastapi import APIRouter, status
from pydantic import BaseModel
from sqlalchemy import text

from sqlalchemy import select

from app.core.config import settings
from app.db.models import GmailAccount
from app.db.session import SessionLocal, engine

log = structlog.get_logger("health")
router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    status: str


class ReadinessComponent(BaseModel):
    status: str
    detail: str | None = None


class ReadyResponse(BaseModel):
    status: str
    database: ReadinessComponent
    qdrant: ReadinessComponent
    gmail: ReadinessComponent


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok")


@router.get(
    "/health/ready",
    response_model=ReadyResponse,
    responses={503: {"model": ReadyResponse}},
)
def ready() -> ReadyResponse:
    database = _check_database()
    qdrant = _check_qdrant()
    gmail = _check_gmail()
    overall = "ok" if database.status == "ok" else "unavailable"
    payload = ReadyResponse(status=overall, database=database, qdrant=qdrant, gmail=gmail)
    if overall != "ok":
        from fastapi.responses import JSONResponse

        return JSONResponse(  # type: ignore[return-value]
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=payload.model_dump(),
        )
    return payload


def _check_database() -> ReadinessComponent:
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return ReadinessComponent(status="ok")
    except Exception as exc:
        log.warning("health.database_unavailable", error=str(exc))
        return ReadinessComponent(status="error", detail="database unreachable")


def _check_gmail() -> ReadinessComponent:
    try:
        with SessionLocal() as db:
            account = db.scalar(select(GmailAccount).order_by(GmailAccount.updated_at.desc()))
        if account is None:
            return ReadinessComponent(status="skipped", detail="no gmail account")
        if account.status == "connected":
            return ReadinessComponent(status="ok", detail=account.email)
        return ReadinessComponent(status="error", detail=account.status)
    except Exception as exc:
        log.warning("health.gmail_unavailable", error=str(exc))
        return ReadinessComponent(status="error", detail="gmail status unreachable")


def _check_qdrant() -> ReadinessComponent:
    if not settings.qdrant_url:
        return ReadinessComponent(status="skipped", detail="QDRANT_URL not configured")
    try:
        from qdrant_client import QdrantClient

        client = QdrantClient(
            url=settings.qdrant_url,
            api_key=settings.qdrant_api_key,
            timeout=2,
        )
        client.get_collections()
        return ReadinessComponent(status="ok")
    except Exception as exc:
        log.warning("health.qdrant_unavailable", error=str(exc))
        return ReadinessComponent(status="error", detail="qdrant unreachable")
