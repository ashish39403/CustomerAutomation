from __future__ import annotations

import math
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from typing import Literal

from pydantic import BaseModel
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.core.errors import NotFoundError
from app.db.models import AiRun, Message, Ticket, User
from app.db.models.enums import TicketStatus
from app.db.session import get_db

router = APIRouter(prefix="/tickets", tags=["tickets"])
stats_router = APIRouter(tags=["stats"])

API_PENDING = {
    TicketStatus.NEW.value,
    TicketStatus.PROCESSING.value,
    TicketStatus.NEEDS_REVIEW.value,
    TicketStatus.APPROVED.value,
}
API_AUTO_REPLIED = {TicketStatus.REPLIED.value}
API_HANDED_OFF = {
    TicketStatus.ESCALATED.value,
    TicketStatus.FAILED.value,
    TicketStatus.RESOLVED.value,
}
API_FILTERS = {
    "pending": API_PENDING,
    "auto_replied": API_AUTO_REPLIED,
    "handed_off": API_HANDED_OFF,
}


def to_api_status(internal: str) -> str:
    if internal in API_AUTO_REPLIED:
        return "auto_replied"
    if internal in API_HANDED_OFF:
        return "handed_off"
    return "pending"


def _parse_ticket_id(raw: str) -> UUID:
    try:
        return UUID(raw)
    except ValueError as exc:
        raise NotFoundError("Ticket not found") from exc


class TicketListItem(BaseModel):
    id: UUID
    customer_email: str
    subject: str | None
    status: str
    created_at: datetime
    updated_at: datetime


class TicketListResponse(BaseModel):
    items: list[TicketListItem]
    total: int
    page: int
    page_size: int
    pages: int


class ThreadMessage(BaseModel):
    id: UUID
    author: str
    body: str | None
    created_at: datetime


class TicketDetailResponse(BaseModel):
    id: UUID
    customer_email: str
    subject: str | None
    status: str
    created_at: datetime
    updated_at: datetime
    messages: list[ThreadMessage]
    classification: str | None
    reasoning: str | None


class StatsResponse(BaseModel):
    auto_replied: int
    handed_off: int
    pending: int
    today_total: int


def _item(ticket: Ticket) -> TicketListItem:
    return TicketListItem(
        id=ticket.id,
        customer_email=ticket.customer_email,
        subject=ticket.subject,
        status=to_api_status(ticket.status),
        created_at=ticket.created_at,
        updated_at=ticket.updated_at,
    )


@router.get("", response_model=TicketListResponse)
def list_tickets(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
    status: Literal["all", "pending", "auto_replied", "handed_off"] = Query(default="all"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    q: str | None = Query(default=None, max_length=200),
) -> TicketListResponse:
    query = select(Ticket)
    count = select(func.count()).select_from(Ticket)
    if status != "all":
        query = query.where(Ticket.status.in_(API_FILTERS[status]))
        count = count.where(Ticket.status.in_(API_FILTERS[status]))
    needle = (q or "").strip()
    if needle:
        like = f"%{needle}%"
        filt = or_(Ticket.customer_email.ilike(like), Ticket.subject.ilike(like))
        query = query.where(filt)
        count = count.where(filt)
    query = query.order_by(Ticket.updated_at.desc(), Ticket.id.desc())
    total = db.scalar(count) or 0
    pages = max(1, math.ceil(total / page_size) if total else 1)
    rows = db.scalars(query.offset((page - 1) * page_size).limit(page_size)).all()
    return TicketListResponse(
        items=[_item(row) for row in rows],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.get("/{ticket_id}", response_model=TicketDetailResponse)
def get_ticket(
    ticket_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> TicketDetailResponse:
    ticket = db.get(Ticket, _parse_ticket_id(ticket_id))
    if ticket is None:
        raise NotFoundError("Ticket not found")
    messages = db.scalars(
        select(Message).where(Message.ticket_id == ticket.id).order_by(Message.created_at)
    ).all()
    run = db.scalar(
        select(AiRun).where(AiRun.ticket_id == ticket.id).order_by(AiRun.created_at.desc())
    )
    thread = []
    for row in messages:
        author = "customer" if row.direction == "inbound" else "bot"
        thread.append(
            ThreadMessage(
                id=row.id,
                author=author,
                body=row.body_text,
                created_at=row.created_at,
            )
        )
    classification = ticket.category
    reasoning = run.decision_reason if run else None
    if run and run.classification_json and not reasoning:
        reasoning = run.classification_json.get("summary")
    return TicketDetailResponse(
        id=ticket.id,
        customer_email=ticket.customer_email,
        subject=ticket.subject,
        status=to_api_status(ticket.status),
        created_at=ticket.created_at,
        updated_at=ticket.updated_at,
        messages=thread,
        classification=classification,
        reasoning=reasoning,
    )


@stats_router.get("/stats", response_model=StatsResponse)
def stats(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> StatsResponse:
    def _count(statuses: set[str]) -> int:
        return db.scalar(
            select(func.count()).select_from(Ticket).where(Ticket.status.in_(statuses))
        ) or 0

    today = db.scalar(
        select(func.count())
        .select_from(Ticket)
        .where(Ticket.created_at >= func.date_trunc("day", func.timezone("UTC", func.now())))
    ) or 0
    return StatsResponse(
        auto_replied=_count(API_AUTO_REPLIED),
        handed_off=_count(API_HANDED_OFF),
        pending=_count(API_PENDING),
        today_total=today,
    )
