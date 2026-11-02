from __future__ import annotations

import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed

import pytest
from sqlalchemy.exc import IntegrityError

from app.db.models import Message, Ticket
from app.db.session import SessionLocal


def _insert_ticket(thread_id: str, customer_email: str) -> str:
    with SessionLocal() as db:
        ticket = Ticket(
            gmail_thread_id=thread_id,
            customer_email=customer_email,
            subject="schema uniqueness",
        )
        db.add(ticket)
        db.commit()
        return str(ticket.id)


def test_duplicate_gmail_thread_id_is_rejected() -> None:
    thread_id = f"thread-{uuid.uuid4()}"
    first_id = _insert_ticket(thread_id, "one@example.com")
    try:
        with pytest.raises(IntegrityError):
            _insert_ticket(thread_id, "two@example.com")
    finally:
        with SessionLocal() as db:
            ticket = db.get(Ticket, uuid.UUID(first_id))
            if ticket is not None:
                db.delete(ticket)
                db.commit()


def test_concurrent_ticket_inserts_keep_one_thread() -> None:
    thread_id = f"thread-{uuid.uuid4()}"
    results: list[object] = []

    def attempt() -> str:
        return _insert_ticket(thread_id, f"{uuid.uuid4()}@example.com")

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(attempt) for _ in range(2)]
        for future in as_completed(futures):
            try:
                results.append(future.result())
            except IntegrityError:
                results.append("conflict")

    created_ids = [item for item in results if item != "conflict"]
    assert len(created_ids) == 1
    assert results.count("conflict") == 1

    with SessionLocal() as db:
        ticket = db.get(Ticket, uuid.UUID(str(created_ids[0])))
        if ticket is not None:
            db.delete(ticket)
            db.commit()


def test_duplicate_gmail_message_id_is_rejected() -> None:
    thread_id = f"thread-{uuid.uuid4()}"
    message_id = f"msg-{uuid.uuid4()}"
    ticket_id = uuid.UUID(_insert_ticket(thread_id, "msg@example.com"))
    try:
        with SessionLocal() as db:
            db.add(
                Message(
                    ticket_id=ticket_id,
                    gmail_message_id=message_id,
                    direction="inbound",
                    from_email="msg@example.com",
                    body_text="hello",
                )
            )
            db.commit()
        with SessionLocal() as db:
            db.add(
                Message(
                    ticket_id=ticket_id,
                    gmail_message_id=message_id,
                    direction="inbound",
                    from_email="msg@example.com",
                    body_text="duplicate",
                )
            )
            with pytest.raises(IntegrityError):
                db.commit()
            db.rollback()
    finally:
        with SessionLocal() as db:
            ticket = db.get(Ticket, ticket_id)
            if ticket is not None:
                db.delete(ticket)
                db.commit()
