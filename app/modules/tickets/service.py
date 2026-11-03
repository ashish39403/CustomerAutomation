from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta
from uuid import UUID

import structlog
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import AppError, ConflictError, NotFoundError
from app.db.models import (
    AiRun,
    AuditEvent,
    Document,
    DocumentChunk,
    GmailAccount,
    Message,
    SendAttempt,
    Ticket,
    User,
)
from app.db.models.enums import (
    ActorType,
    Decision,
    GmailAccountStatus,
    MessageDirection,
    SendAttemptStatus,
    TicketStatus,
)
from app.modules.gmail.send import (
    AUTHOR_HEADER,
    GmailSendRejected,
    GmailSendUnknown,
    SendResult,
    find_matching_outbound,
    send_thread_reply,
)

log = structlog.get_logger("tickets")

SENDABLE = {
    TicketStatus.NEW.value,
    TicketStatus.PROCESSING.value,
    TicketStatus.NEEDS_REVIEW.value,
    TicketStatus.APPROVED.value,
    TicketStatus.ESCALATED.value,
    TicketStatus.FAILED.value,
    TicketStatus.REPLIED.value,
    TicketStatus.AUTO_REPLIED.value,
    TicketStatus.RESOLVED.value,
}
ESCALATE_FROM = {
    TicketStatus.NEW.value,
    TicketStatus.PROCESSING.value,
    TicketStatus.NEEDS_REVIEW.value,
    TicketStatus.APPROVED.value,
    TicketStatus.FAILED.value,
}
RESOLVE_FROM = {
    TicketStatus.NEW.value,
    TicketStatus.PROCESSING.value,
    TicketStatus.NEEDS_REVIEW.value,
    TicketStatus.APPROVED.value,
    TicketStatus.ESCALATED.value,
    TicketStatus.REPLIED.value,
    TicketStatus.AUTO_REPLIED.value,
    TicketStatus.FAILED.value,
}
REOPEN_FROM = {
    TicketStatus.RESOLVED.value,
    TicketStatus.ESCALATED.value,
    TicketStatus.REPLIED.value,
    TicketStatus.AUTO_REPLIED.value,
    TicketStatus.FAILED.value,
}
DRAFT_FROM = {
    TicketStatus.NEW.value,
    TicketStatus.PROCESSING.value,
    TicketStatus.NEEDS_REVIEW.value,
    TicketStatus.APPROVED.value,
    TicketStatus.ESCALATED.value,
    TicketStatus.FAILED.value,
}
IN_FLIGHT = {SendAttemptStatus.PENDING.value, SendAttemptStatus.UNKNOWN.value}
STALE_PENDING = timedelta(minutes=2)


def send_automated_reply(db: Session, ticket_id: UUID, body: str) -> Message:
    """Send a grounded draft as the bot. A failure leaves the ticket unsent."""
    return reply_to_ticket(db, ticket_id, body, actor=None, automated=True)


def reply_to_ticket(
    db: Session,
    ticket_id: UUID,
    body: str,
    actor: User | None,
    *,
    automated: bool = False,
) -> Message:
    ticket = _lock_ticket(db, ticket_id)
    _assert_sendable(ticket)
    account = _connected_account(db)
    inbound = _latest_inbound(db, ticket.id)
    key = _idempotency_key(ticket.id, body, automated=automated)
    attempt = db.scalar(select(SendAttempt).where(SendAttempt.idempotency_key == key))
    now = datetime.now(UTC)

    if attempt is not None and attempt.status == SendAttemptStatus.SENT.value:
        existing = _message_for_gmail_id(db, attempt.gmail_message_id)
        if existing is not None:
            return existing

    if attempt is not None and attempt.status == SendAttemptStatus.PENDING.value:
        if attempt.attempted_at and now - attempt.attempted_at < STALE_PENDING:
            raise ConflictError("A send is already in progress")
        attempt.status = SendAttemptStatus.UNKNOWN.value

    if attempt is not None and attempt.status == SendAttemptStatus.UNKNOWN.value:
        matched = find_matching_outbound(
            account.encrypted_refresh_token or "",
            thread_id=ticket.gmail_thread_id,
            mailbox=account.email,
            after=attempt.attempted_at or attempt.created_at,
        )
        if matched:
            return _complete_sent(
                db,
                ticket,
                attempt,
                actor,
                body,
                account,
                inbound,
                matched,
                automated=automated,
            )
        attempt.status = SendAttemptStatus.PENDING.value

    if attempt is None:
        attempt = SendAttempt(
            ticket_id=ticket.id,
            ai_run_id=_latest_run_id(db, ticket.id),
            idempotency_key=key,
            status=SendAttemptStatus.PENDING.value,
            attempted_at=now,
        )
        db.add(attempt)
        db.flush()
    else:
        attempt.status = SendAttemptStatus.PENDING.value
        attempt.attempted_at = now
        attempt.error = None
        attempt.completed_at = None

    db.add(
        AuditEvent(
            actor_type=ActorType.WORKER.value if automated else ActorType.USER.value,
            actor_id=None if actor is None else actor.id,
            ticket_id=ticket.id,
            event_type="ticket.send_started",
            event_data_json={"send_attempt_id": str(attempt.id)},
        )
    )
    db.commit()
    db.refresh(attempt)
    db.refresh(ticket)

    try:
        result = send_thread_reply(
            account.encrypted_refresh_token or "",
            mailbox=account.email,
            to=ticket.customer_email,
            subject=ticket.subject,
            body=body,
            thread_id=ticket.gmail_thread_id,
            in_reply_to=_header(inbound.headers_json if inbound else None, "Message-ID"),
            references=_header(inbound.headers_json if inbound else None, "References"),
        )
    except GmailSendUnknown as exc:
        _mark_attempt(db, attempt.id, SendAttemptStatus.UNKNOWN.value, error=str(exc))
        matched = find_matching_outbound(
            account.encrypted_refresh_token or "",
            thread_id=ticket.gmail_thread_id,
            mailbox=account.email,
            after=now,
        )
        if matched:
            db.refresh(ticket)
            db.refresh(attempt)
            return _complete_sent(
                db,
                ticket,
                attempt,
                actor,
                body,
                account,
                inbound,
                matched,
                automated=automated,
            )
        raise AppError("Could not send the reply", status_code=502, code="gmail_send_failed") from exc
    except GmailSendRejected as exc:
        _mark_attempt(db, attempt.id, SendAttemptStatus.FAILED.value, error=str(exc))
        raise AppError("Could not send the reply", status_code=502, code="gmail_send_failed") from exc
    except Exception as exc:
        _mark_attempt(db, attempt.id, SendAttemptStatus.UNKNOWN.value, error=str(exc))
        raise AppError("Could not send the reply", status_code=502, code="gmail_send_failed") from exc

    db.refresh(ticket)
    db.refresh(attempt)
    return _complete_sent(
        db,
        ticket,
        attempt,
        actor,
        body,
        account,
        inbound,
        result.gmail_message_id,
        result,
        automated=automated,
    )


def save_draft(db: Session, ticket_id: UUID, body: str, actor: User) -> AiRun:
    ticket = _lock_ticket(db, ticket_id)
    if ticket.status not in DRAFT_FROM:
        raise ConflictError("Draft cannot be edited in this ticket state")
    run = _latest_run(db, ticket.id)
    if run is None:
        run = AiRun(
            ticket_id=ticket.id,
            draft_text=body,
            decision=Decision.NEEDS_REVIEW.value,
            decision_reason="Operator draft saved before classification finished",
        )
        db.add(run)
        db.flush()
    else:
        run.draft_text = body
    ticket.updated_at = datetime.now(UTC)
    db.add(
        AuditEvent(
            actor_type=ActorType.USER.value,
            actor_id=actor.id,
            ticket_id=ticket.id,
            event_type="ticket.draft_saved",
            event_data_json={"ai_run_id": str(run.id)},
        )
    )
    db.commit()
    db.refresh(run)
    return run


def escalate_ticket(db: Session, ticket_id: UUID, actor: User) -> Ticket:
    ticket = _lock_ticket(db, ticket_id)
    if ticket.status == TicketStatus.ESCALATED.value:
        return ticket
    if ticket.status not in ESCALATE_FROM:
        raise ConflictError("Ticket cannot be escalated from this state")
    ticket.status = TicketStatus.ESCALATED.value
    _audit(db, ticket, actor, "ticket.escalated")
    db.commit()
    db.refresh(ticket)
    return ticket


def resolve_ticket(db: Session, ticket_id: UUID, actor: User) -> Ticket:
    ticket = _lock_ticket(db, ticket_id)
    if ticket.status == TicketStatus.RESOLVED.value:
        return ticket
    if ticket.status not in RESOLVE_FROM:
        raise ConflictError("Ticket cannot be resolved from this state")
    ticket.status = TicketStatus.RESOLVED.value
    ticket.resolved_at = datetime.now(UTC)
    _audit(db, ticket, actor, "ticket.resolved")
    db.commit()
    db.refresh(ticket)
    return ticket


def reopen_ticket(db: Session, ticket_id: UUID, actor: User) -> Ticket:
    ticket = _lock_ticket(db, ticket_id)
    if ticket.status not in REOPEN_FROM:
        raise ConflictError("Ticket cannot be reopened from this state")
    ticket.status = TicketStatus.NEEDS_REVIEW.value
    ticket.resolved_at = None
    _audit(db, ticket, actor, "ticket.reopened")
    db.commit()
    db.refresh(ticket)
    return ticket


def list_ticket_audit(db: Session, ticket_id: UUID) -> list[AuditEvent]:
    ticket = db.get(Ticket, ticket_id)
    if ticket is None:
        raise NotFoundError("Ticket not found")
    return list(
        db.scalars(
            select(AuditEvent)
            .where(AuditEvent.ticket_id == ticket.id)
            .order_by(AuditEvent.created_at.desc(), AuditEvent.id.desc())
        ).all()
    )


def latest_run(db: Session, ticket_id: UUID) -> AiRun | None:
    return _latest_run(db, ticket_id)


def risk_flags_for(run: AiRun | None) -> list[str] | None:
    if run is None:
        return None
    payload = run.risk_flags_json if isinstance(run.risk_flags_json, dict) else {}
    raw = payload.get("flags")
    if not isinstance(raw, list):
        return []
    return [str(flag) for flag in raw if str(flag).strip()]


def sources_for(db: Session, run: AiRun | None) -> list[dict[str, str | None]] | None:
    if run is None:
        return None
    raw_ids = run.retrieved_chunk_ids if isinstance(run.retrieved_chunk_ids, list) else []
    ordered: list[str] = []
    for item in raw_ids:
        text = str(item).strip()
        if text and text not in ordered:
            ordered.append(text)
    if not ordered:
        return []

    uuids: list[UUID] = []
    for raw in ordered:
        try:
            uuids.append(UUID(raw))
        except ValueError:
            continue
    clauses = [DocumentChunk.qdrant_point_id.in_(ordered)]
    if uuids:
        clauses.append(DocumentChunk.id.in_(uuids))
    rows = list(db.scalars(select(DocumentChunk).where(or_(*clauses))).all())
    by_point = {row.qdrant_point_id: row for row in rows if row.qdrant_point_id}
    by_id = {str(row.id): row for row in rows}
    documents = {
        document.id: document
        for document in db.scalars(
            select(Document).where(Document.id.in_({row.document_id for row in rows}))
        ).all()
    } if rows else {}

    sources: list[dict[str, str | None]] = []
    for raw in ordered:
        row = by_point.get(raw) or by_id.get(raw)
        title = None
        locator = None
        if row is not None:
            locator = row.source_locator
            document = documents.get(row.document_id)
            title = document.title if document is not None else None
        sources.append({"id": raw, "title": title, "locator": locator, "excerpt": None})
    return sources


def assign_ticket(db: Session, ticket_id: UUID, assigned_to: UUID | None, actor: User) -> Ticket:
    ticket = _lock_ticket(db, ticket_id)
    if assigned_to is not None:
        user = db.get(User, assigned_to)
        if user is None:
            raise NotFoundError("User not found")
    ticket.assigned_to = assigned_to
    db.add(
        AuditEvent(
            actor_type=ActorType.USER.value,
            actor_id=actor.id,
            ticket_id=ticket.id,
            event_type="ticket.assigned",
            event_data_json={"assigned_to": str(assigned_to) if assigned_to else None},
        )
    )
    db.commit()
    db.refresh(ticket)
    return ticket


def _lock_ticket(db: Session, ticket_id: UUID) -> Ticket:
    ticket = db.scalar(select(Ticket).where(Ticket.id == ticket_id).with_for_update())
    if ticket is None:
        raise NotFoundError("Ticket not found")
    return ticket


def _assert_sendable(ticket: Ticket) -> None:
    if ticket.status not in SENDABLE:
        raise ConflictError("Ticket cannot be sent from this state")
    if not ticket.gmail_thread_id:
        raise ConflictError("Ticket has no Gmail thread")


def _connected_account(db: Session) -> GmailAccount:
    account = db.scalar(
        select(GmailAccount)
        .where(GmailAccount.status == GmailAccountStatus.CONNECTED.value)
        .order_by(GmailAccount.updated_at.desc())
    )
    if account is None or not account.encrypted_refresh_token or not account.email:
        raise AppError("Could not send the reply", status_code=502, code="gmail_send_failed")
    return account


def _latest_inbound(db: Session, ticket_id: UUID) -> Message | None:
    return db.scalar(
        select(Message)
        .where(
            Message.ticket_id == ticket_id,
            Message.direction == MessageDirection.INBOUND.value,
        )
        .order_by(Message.created_at.desc())
    )


def _latest_run(db: Session, ticket_id: UUID) -> AiRun | None:
    return db.scalar(
        select(AiRun).where(AiRun.ticket_id == ticket_id).order_by(AiRun.created_at.desc())
    )


def _latest_run_id(db: Session, ticket_id: UUID) -> UUID | None:
    run = _latest_run(db, ticket_id)
    return run.id if run is not None else None


def _idempotency_key(ticket_id: UUID, body: str, *, automated: bool = False) -> str:
    digest = hashlib.sha256(body.encode("utf-8")).hexdigest()[:32]
    kind = "bot" if automated else "human"
    return f"{ticket_id}:{kind}:{digest}"


def _header(headers: dict | None, name: str) -> str | None:
    if not headers:
        return None
    target = name.lower()
    for key, value in headers.items():
        if key.lower() == target and value:
            return str(value)
    return None


def _message_for_gmail_id(db: Session, gmail_message_id: str | None) -> Message | None:
    if not gmail_message_id:
        return None
    return db.scalar(select(Message).where(Message.gmail_message_id == gmail_message_id))


def _mark_attempt(db: Session, attempt_id: UUID, status: str, *, error: str | None) -> None:
    attempt = db.get(SendAttempt, attempt_id)
    if attempt is None:
        return
    attempt.status = status
    attempt.error = (error or "")[:4000] or None
    if status != SendAttemptStatus.PENDING.value:
        attempt.completed_at = datetime.now(UTC)
    db.commit()
    log.info("tickets.send_attempt", send_attempt_id=str(attempt_id), status=status)


def _complete_sent(
    db: Session,
    ticket: Ticket,
    attempt: SendAttempt,
    actor: User | None,
    body: str,
    account: GmailAccount,
    inbound: Message | None,
    gmail_message_id: str,
    result: SendResult | None = None,
    *,
    automated: bool = False,
) -> Message:
    existing = _message_for_gmail_id(db, gmail_message_id)
    now = datetime.now(UTC)
    if existing is None:
        existing = Message(
            ticket_id=ticket.id,
            gmail_message_id=gmail_message_id,
            direction=MessageDirection.OUTBOUND.value,
            from_email=account.email,
            to_emails=[ticket.customer_email],
            subject=ticket.subject,
            body_text=body,
            sent_at=now,
            headers_json={AUTHOR_HEADER: "bot" if automated else "human"},
        )
        db.add(existing)
        try:
            with db.begin_nested():
                db.flush()
        except IntegrityError:
            existing = _message_for_gmail_id(db, gmail_message_id)
            if existing is None:
                raise
    attempt.status = SendAttemptStatus.SENT.value
    attempt.gmail_message_id = gmail_message_id
    attempt.completed_at = now
    attempt.error = None
    ticket.status = (
        TicketStatus.AUTO_REPLIED.value if automated else TicketStatus.REPLIED.value
    )
    ticket.last_message_at = now
    db.add(
        AuditEvent(
            actor_type=ActorType.WORKER.value if automated else ActorType.USER.value,
            actor_id=None if actor is None else actor.id,
            ticket_id=ticket.id,
            event_type="ticket.auto_replied" if automated else "ticket.replied",
            event_data_json={
                "send_attempt_id": str(attempt.id),
                "gmail_message_id": gmail_message_id,
                "thread_id": result.thread_id if result else ticket.gmail_thread_id,
                "inbound_message_id": str(inbound.id) if inbound else None,
            },
        )
    )
    db.commit()
    db.refresh(existing)
    log.info(
        "tickets.replied",
        ticket_id=str(ticket.id),
        send_attempt_id=str(attempt.id),
        gmail_message_id=gmail_message_id,
    )
    return existing


def _audit(db: Session, ticket: Ticket, actor: User, event_type: str) -> None:
    db.add(
        AuditEvent(
            actor_type=ActorType.USER.value,
            actor_id=actor.id,
            ticket_id=ticket.id,
            event_type=event_type,
            event_data_json={"status": ticket.status},
        )
    )
