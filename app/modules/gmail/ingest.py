from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models import AuditEvent, Message, Ticket
from app.db.models.enums import ActorType, JobType, MessageDirection, TicketStatus
from app.modules.gmail.guards import skip_reason
from app.modules.gmail.schemas import NormalizedEmail
from app.modules.jobs.queue import enqueue

log = structlog.get_logger("gmail")


@dataclass(frozen=True, slots=True)
class IngestResult:
    created: bool
    skipped: bool
    reason: str | None = None
    ticket_id: UUID | None = None
    message_id: UUID | None = None


def ingest_email(db: Session, email: NormalizedEmail, mailbox_email: str) -> IngestResult:
    existing = db.scalar(
        select(Message.id).where(Message.gmail_message_id == email.gmail_message_id)
    )
    if existing is not None:
        return IngestResult(created=False, skipped=False, reason="duplicate", message_id=existing)

    skipped = skip_reason(email, mailbox_email)
    if skipped is not None:
        db.add(
            AuditEvent(
                actor_type=ActorType.SYSTEM.value,
                event_type="gmail.skipped",
                event_data_json={
                    "gmail_message_id": email.gmail_message_id,
                    "code": skipped.code,
                    "detail": skipped.detail,
                },
            )
        )
        log.info(
            "gmail.skipped",
            gmail_message_id=email.gmail_message_id,
            reason=skipped.code,
            detail=skipped.detail,
        )
        return IngestResult(created=False, skipped=True, reason=skipped.code)

    ticket = db.scalar(select(Ticket).where(Ticket.gmail_thread_id == email.gmail_thread_id))
    if ticket is None:
        ticket = Ticket(
            gmail_thread_id=email.gmail_thread_id,
            customer_email=email.from_email,
            subject=email.subject,
            status=TicketStatus.NEW.value,
            last_message_at=email.received_at,
        )
        db.add(ticket)
        try:
            with db.begin_nested():
                db.flush()
        except IntegrityError:
            ticket = db.scalar(
                select(Ticket).where(Ticket.gmail_thread_id == email.gmail_thread_id)
            )
            if ticket is None:
                raise

    message = Message(
        ticket_id=ticket.id,
        gmail_message_id=email.gmail_message_id,
        direction=MessageDirection.INBOUND.value,
        from_email=email.from_email,
        to_emails=email.to_emails,
        subject=email.subject,
        body_text=email.body_text,
        received_at=email.received_at,
        headers_json=email.headers,
        attachments_metadata_json=[item.model_dump() for item in email.attachments],
    )
    db.add(message)
    try:
        with db.begin_nested():
            db.flush()
    except IntegrityError:
        return IngestResult(created=False, skipped=False, reason="duplicate")

    ticket.last_message_at = email.received_at or ticket.last_message_at
    job = enqueue(
        db,
        JobType.PROCESS_EMAIL.value,
        {"ticket_id": str(ticket.id), "message_id": str(message.id)},
    )
    db.add(
        AuditEvent(
            actor_type=ActorType.SYSTEM.value,
            ticket_id=ticket.id,
            event_type="gmail.ingested",
            event_data_json={
                "gmail_message_id": email.gmail_message_id,
                "job_id": str(job.id),
            },
        )
    )
    log.info(
        "gmail.ingested",
        ticket_id=str(ticket.id),
        message_id=str(message.id),
        gmail_message_id=email.gmail_message_id,
    )
    return IngestResult(
        created=True,
        skipped=False,
        ticket_id=ticket.id,
        message_id=message.id,
    )
