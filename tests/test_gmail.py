from __future__ import annotations

import uuid

from sqlalchemy import select

from app.db.models import AuditEvent, Job, Message, Ticket
from app.db.session import SessionLocal
from app.modules.gmail.guards import skip_reason
from app.modules.gmail.ingest import ingest_email
from app.modules.gmail.normalize import normalize_message
from app.modules.gmail.schemas import NormalizedEmail

MAILBOX = "support@harborandpine.test"


def _email(**overrides: object) -> NormalizedEmail:
    data = {
        "gmail_message_id": f"msg-{uuid.uuid4()}",
        "gmail_thread_id": f"thread-{uuid.uuid4()}",
        "from_email": "customer@example.com",
        "to_emails": [MAILBOX],
        "subject": "Where is my order?",
        "body_text": "Need a tracking update",
        "headers": {"From": "Customer <customer@example.com>"},
    }
    data.update(overrides)
    return NormalizedEmail.model_validate(data)


def _cleanup(thread_id: str) -> None:
    with SessionLocal() as db:
        ticket = db.scalar(select(Ticket).where(Ticket.gmail_thread_id == thread_id))
        if ticket is None:
            return
        jobs = db.scalars(select(Job)).all()
        for job in jobs:
            if (job.payload_json or {}).get("ticket_id") == str(ticket.id):
                db.delete(job)
        db.delete(ticket)
        db.commit()


def test_self_sent_and_auto_reply_are_skipped() -> None:
    self_sent = _email(from_email=MAILBOX)
    auto = _email(headers={"Auto-Submitted": "auto-replied"}, subject="Auto: received")
    assert skip_reason(self_sent, MAILBOX).code == "self_sent"
    assert skip_reason(auto, MAILBOX).code == "auto_reply"


def test_ingest_creates_ticket_message_and_job_once() -> None:
    email = _email()
    try:
        with SessionLocal() as db:
            first = ingest_email(db, email, MAILBOX)
            db.commit()
            second = ingest_email(db, email, MAILBOX)
            db.commit()
        assert first.created is True
        assert second.created is False
        assert second.reason == "duplicate"
        with SessionLocal() as db:
            tickets = db.scalars(select(Ticket).where(Ticket.gmail_thread_id == email.gmail_thread_id)).all()
            messages = db.scalars(
                select(Message).where(Message.gmail_message_id == email.gmail_message_id)
            ).all()
            jobs = [
                job
                for job in db.scalars(select(Job)).all()
                if (job.payload_json or {}).get("ticket_id") == str(first.ticket_id)
            ]
            assert len(tickets) == 1
            assert len(messages) == 1
            assert len(jobs) == 1
    finally:
        _cleanup(email.gmail_thread_id)


def test_skipped_mail_does_not_create_a_ticket() -> None:
    email = _email(from_email=MAILBOX, gmail_thread_id=f"thread-{uuid.uuid4()}")
    with SessionLocal() as db:
        result = ingest_email(db, email, MAILBOX)
        db.commit()
        assert result.skipped is True
        assert db.scalar(select(Ticket).where(Ticket.gmail_thread_id == email.gmail_thread_id)) is None
        event = db.scalar(
            select(AuditEvent).where(AuditEvent.event_type == "gmail.skipped").order_by(
                AuditEvent.created_at.desc()
            )
        )
        assert event is not None


def test_normalize_message_extracts_headers_and_body() -> None:
    raw = {
        "id": "abc123",
        "threadId": "thr1",
        "internalDate": "1710000000000",
        "payload": {
            "mimeType": "text/plain",
            "headers": [
                {"name": "From", "value": "Ada <ada@example.com>"},
                {"name": "To", "value": MAILBOX},
                {"name": "Subject", "value": "Help"},
            ],
            "body": {"data": "aGVsbG8gd29ybGQ="},
        },
    }
    email = normalize_message(raw)
    assert email.from_email == "ada@example.com"
    assert email.subject == "Help"
    assert email.body_text == "hello world"
    assert email.gmail_thread_id == "thr1"
