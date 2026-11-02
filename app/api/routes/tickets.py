from __future__ import annotations

import math
from datetime import datetime
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.core.errors import NotFoundError
from app.db.models import AiRun, Message, Ticket, User
from app.db.models.enums import MessageDirection, TicketStatus
from app.db.session import get_db
from app.modules.gmail.send import AUTHOR_HEADER
from app.modules.tickets.service import (
    assign_ticket,
    escalate_ticket,
    reopen_ticket,
    reply_to_ticket,
    resolve_ticket,
    save_draft,
)

router = APIRouter(prefix="/tickets", tags=["tickets"])
stats_router = APIRouter(tags=["stats"])

API_PENDING = {
    TicketStatus.NEW.value,
    TicketStatus.PROCESSING.value,
    TicketStatus.NEEDS_REVIEW.value,
    TicketStatus.APPROVED.value,
}
# Auto-send is hard-disabled. Human dashboard send maps to handed_off.
API_AUTO_REPLIED: set[str] = set()
API_HANDED_OFF = {
    TicketStatus.REPLIED.value,
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


class ReplyRequest(BaseModel):
    body: str = Field(..., min_length=1, max_length=10000)

    @field_validator("body")
    @classmethod
    def strip_body(cls, value: str) -> str:
        text = value.strip()
        if not text:
            raise ValueError("body must be non-empty")
        if len(text) > 10000:
            raise ValueError("body is too long")
        return text


class DraftRequest(ReplyRequest):
    pass


class AssignRequest(BaseModel):
    assigned_to: UUID | None = None


class TicketActionResponse(BaseModel):
    id: UUID
    status: str
    assigned_to: UUID | None = None


class DraftResponse(BaseModel):
    ticket_id: UUID
    body: str
    updated_at: datetime


def _item(ticket: Ticket) -> TicketListItem:
    return TicketListItem(
        id=ticket.id,
        customer_email=ticket.customer_email,
        subject=ticket.subject,
        status=to_api_status(ticket.status),
        created_at=ticket.created_at,
        updated_at=ticket.updated_at,
    )


def _author(message: Message) -> str:
    if message.direction == MessageDirection.INBOUND.value:
        return "customer"
    headers = message.headers_json or {}
    value = headers.get(AUTHOR_HEADER) or headers.get("Ca-Author")
    if str(value or "").lower() == "human":
        return "human"
    return "bot"


def _thread_message(message: Message) -> ThreadMessage:
    return ThreadMessage(
        id=message.id,
        author=_author(message),
        body=message.body_text,
        created_at=message.sent_at or message.created_at,
    )


def _action(ticket: Ticket) -> TicketActionResponse:
    return TicketActionResponse(
        id=ticket.id,
        status=to_api_status(ticket.status),
        assigned_to=ticket.assigned_to,
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
        values = API_FILTERS[status]
        if not values:
            return TicketListResponse(items=[], total=0, page=page, page_size=page_size, pages=1)
        query = query.where(Ticket.status.in_(values))
        count = count.where(Ticket.status.in_(values))
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
        messages=[_thread_message(row) for row in messages],
        classification=classification,
        reasoning=reasoning,
    )


@router.post("/{ticket_id}/reply", response_model=ThreadMessage)
def post_reply(
    ticket_id: str,
    payload: ReplyRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ThreadMessage:
    message = reply_to_ticket(db, _parse_ticket_id(ticket_id), payload.body, user)
    return _thread_message(message)


@router.patch("/{ticket_id}/draft", response_model=DraftResponse)
def patch_draft(
    ticket_id: str,
    payload: DraftRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> DraftResponse:
    run = save_draft(db, _parse_ticket_id(ticket_id), payload.body, user)
    return DraftResponse(
        ticket_id=run.ticket_id,
        body=run.draft_text or "",
        updated_at=run.created_at,
    )


@router.post("/{ticket_id}/escalate", response_model=TicketActionResponse)
def post_escalate(
    ticket_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> TicketActionResponse:
    return _action(escalate_ticket(db, _parse_ticket_id(ticket_id), user))


@router.post("/{ticket_id}/resolve", response_model=TicketActionResponse)
def post_resolve(
    ticket_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> TicketActionResponse:
    return _action(resolve_ticket(db, _parse_ticket_id(ticket_id), user))


@router.post("/{ticket_id}/reopen", response_model=TicketActionResponse)
def post_reopen(
    ticket_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> TicketActionResponse:
    return _action(reopen_ticket(db, _parse_ticket_id(ticket_id), user))


@router.post("/{ticket_id}/assign", response_model=TicketActionResponse)
def post_assign(
    ticket_id: str,
    payload: AssignRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> TicketActionResponse:
    return _action(assign_ticket(db, _parse_ticket_id(ticket_id), payload.assigned_to, user))


@stats_router.get("/stats", response_model=StatsResponse)
def stats(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> StatsResponse:
    def _count(statuses: set[str]) -> int:
        if not statuses:
            return 0
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
