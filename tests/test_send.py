from __future__ import annotations

import uuid

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.config import settings
from app.db.models import AiRun, GmailAccount, Job, Message, SendAttempt, Ticket
from app.db.models.enums import (
    GmailAccountStatus,
    MessageDirection,
    SendAttemptStatus,
    TicketStatus,
)
from app.db.session import SessionLocal
from app.modules.gmail.send import GmailSendRejected, GmailSendUnknown, build_reply_payload


def _login(client: TestClient) -> None:
    response = client.post(
        "/api/auth/login",
        json={
            "email": settings.dashboard_username,
            "password": settings.dashboard_password,
        },
    )
    assert response.status_code == 200


def _seed_ticket(
    *,
    status: str = TicketStatus.NEEDS_REVIEW.value,
    with_run: bool = True,
) -> uuid.UUID:
    with SessionLocal() as db:
        account = GmailAccount(
            email=f"support-{uuid.uuid4().hex[:10]}@harborandpine.test",
            encrypted_refresh_token="test-token",
            status=GmailAccountStatus.CONNECTED.value,
        )
        db.add(account)
        ticket = Ticket(
            gmail_thread_id=f"thread-{uuid.uuid4()}",
            customer_email="customer@example.com",
            subject="Where is my order?",
            status=status,
        )
        db.add(ticket)
        db.flush()
        db.add(
            Message(
                ticket_id=ticket.id,
                gmail_message_id=f"msg-{uuid.uuid4()}",
                direction=MessageDirection.INBOUND.value,
                from_email="customer@example.com",
                to_emails=[account.email],
                subject=ticket.subject,
                body_text="Need a tracking update",
                headers_json={"Message-ID": "<cust@mail>"},
            )
        )
        if with_run:
            db.add(
                AiRun(
                    ticket_id=ticket.id,
                    draft_text="Original draft",
                    decision="needs_review",
                    decision_reason="grounded draft ready for human approval",
                    risk_flags_json={"flags": ["chargeback"]},
                    retrieved_chunk_ids=["missing-chunk"],
                )
            )
        db.commit()
        return ticket.id


def _cleanup(ticket_id: uuid.UUID) -> None:
    with SessionLocal() as db:
        ticket = db.get(Ticket, ticket_id)
        if ticket is None:
            return
        mailbox = db.scalar(
            select(Message.to_emails)
            .where(
                Message.ticket_id == ticket_id,
                Message.direction == MessageDirection.INBOUND.value,
            )
            .limit(1)
        )
        for job in db.scalars(select(Job)).all():
            if (job.payload_json or {}).get("ticket_id") == str(ticket.id):
                db.delete(job)
        db.delete(ticket)
        for email in mailbox or []:
            account = db.scalar(select(GmailAccount).where(GmailAccount.email == email))
            if account is not None:
                db.delete(account)
        db.commit()


def test_build_reply_stays_in_thread() -> None:
    payload = build_reply_payload(
        mailbox="support@test.local",
        to="customer@example.com",
        subject="Where is my order?",
        body="Here is the tracking number.",
        thread_id="thr-1",
        in_reply_to="<cust@mail>",
        references=None,
    )
    assert payload["threadId"] == "thr-1"
    assert payload["raw"]


def test_reply_sends_once_and_marks_handed_off(client: TestClient, monkeypatch) -> None:
    ticket_id = _seed_ticket()
    calls: list[str] = []

    def fake_send(*args, **kwargs):
        calls.append(kwargs["body"])
        from app.modules.gmail.send import SendResult

        return SendResult(gmail_message_id=f"out-{uuid.uuid4()}", thread_id="thr")

    monkeypatch.setattr("app.modules.tickets.service.send_thread_reply", fake_send)
    monkeypatch.setattr("app.modules.tickets.service.find_matching_outbound", lambda *a, **k: None)
    try:
        _login(client)
        body = "Your replacement ships today."
        first = client.post(f"/api/tickets/{ticket_id}/reply", json={"body": body})
        assert first.status_code == 200, first.text
        payload = first.json()
        assert payload["author"] == "human"
        assert payload["body"] == body

        second = client.post(f"/api/tickets/{ticket_id}/reply", json={"body": body})
        assert second.status_code == 200
        assert second.json()["id"] == payload["id"]
        assert calls == [body]

        detail = client.get(f"/api/tickets/{ticket_id}")
        assert detail.status_code == 200
        assert detail.json()["status"] == "handed_off"
        assert detail.json()["messages"][-1]["author"] == "human"

        with SessionLocal() as db:
            ticket = db.get(Ticket, ticket_id)
            assert ticket is not None
            assert ticket.status == TicketStatus.REPLIED.value
            attempt = db.scalar(select(SendAttempt).where(SendAttempt.ticket_id == ticket_id))
            assert attempt is not None
            assert attempt.status == SendAttemptStatus.SENT.value
    finally:
        _cleanup(ticket_id)


def test_failed_send_does_not_mark_replied(client: TestClient, monkeypatch) -> None:
    ticket_id = _seed_ticket()

    def fake_send(*args, **kwargs):
        raise GmailSendRejected("gmail 400")

    monkeypatch.setattr("app.modules.tickets.service.send_thread_reply", fake_send)
    monkeypatch.setattr("app.modules.tickets.service.find_matching_outbound", lambda *a, **k: None)
    try:
        _login(client)
        response = client.post(
            f"/api/tickets/{ticket_id}/reply",
            json={"body": "Could not ship this."},
        )
        assert response.status_code == 502
        assert response.json()["code"] == "gmail_send_failed"
        detail = client.get(f"/api/tickets/{ticket_id}")
        assert detail.json()["status"] == "pending"
        with SessionLocal() as db:
            ticket = db.get(Ticket, ticket_id)
            assert ticket is not None
            assert ticket.status == TicketStatus.NEEDS_REVIEW.value
            attempt = db.scalar(select(SendAttempt).where(SendAttempt.ticket_id == ticket_id))
            assert attempt is not None
            assert attempt.status == SendAttemptStatus.FAILED.value
    finally:
        _cleanup(ticket_id)


def test_unknown_send_reconciles_instead_of_duplicate(client: TestClient, monkeypatch) -> None:
    ticket_id = _seed_ticket()
    calls = {"send": 0, "find": 0}

    def fake_send(*args, **kwargs):
        calls["send"] += 1
        raise GmailSendUnknown("timeout")

    def fake_find(*args, **kwargs):
        calls["find"] += 1
        return "gmail-reconciled-1" if calls["find"] >= 2 else None

    monkeypatch.setattr("app.modules.tickets.service.send_thread_reply", fake_send)
    monkeypatch.setattr("app.modules.tickets.service.find_matching_outbound", fake_find)
    try:
        _login(client)
        body = {"body": "Tracking is on the way."}
        first = client.post(f"/api/tickets/{ticket_id}/reply", json=body)
        assert first.status_code == 502
        second = client.post(f"/api/tickets/{ticket_id}/reply", json=body)
        assert second.status_code == 200, second.text
        assert second.json()["author"] == "human"
        assert calls["send"] == 1
        with SessionLocal() as db:
            attempt = db.scalar(select(SendAttempt).where(SendAttempt.ticket_id == ticket_id))
            assert attempt is not None
            assert attempt.status == SendAttemptStatus.SENT.value
            assert attempt.gmail_message_id == "gmail-reconciled-1"
    finally:
        _cleanup(ticket_id)


def test_reply_contract_errors(client: TestClient) -> None:
    _login(client)
    missing = client.post("/api/tickets/not-a-uuid/reply", json={"body": "hello"})
    assert missing.status_code == 404
    empty = client.post(
        f"/api/tickets/{uuid.uuid4()}/reply",
        json={"body": "   "},
    )
    assert empty.status_code == 422
    unknown = client.post(f"/api/tickets/{uuid.uuid4()}/reply", json={"body": "hello"})
    assert unknown.status_code == 404


def test_reply_requires_session(client: TestClient) -> None:
    response = client.post(f"/api/tickets/{uuid.uuid4()}/reply", json={"body": "hello"})
    assert response.status_code == 401


def test_escalate_resolve_reopen_and_draft(client: TestClient) -> None:
    ticket_id = _seed_ticket()
    try:
        _login(client)
        draft = client.patch(
            f"/api/tickets/{ticket_id}/draft",
            json={"body": "Edited draft for the customer."},
        )
        assert draft.status_code == 200, draft.text
        assert draft.json()["body"] == "Edited draft for the customer."

        escalated = client.post(f"/api/tickets/{ticket_id}/escalate")
        assert escalated.status_code == 200
        assert escalated.json()["status"] == "handed_off"

        reopened = client.post(f"/api/tickets/{ticket_id}/reopen")
        assert reopened.status_code == 200
        assert reopened.json()["status"] == "pending"

        resolved = client.post(f"/api/tickets/{ticket_id}/resolve")
        assert resolved.status_code == 200
        assert resolved.json()["status"] == "handed_off"

        me = client.get("/api/auth/me").json()
        assigned = client.post(
            f"/api/tickets/{ticket_id}/assign",
            json={"assigned_to": me["id"]},
        )
        assert assigned.status_code == 200
        assert assigned.json()["assigned_to"] == me["id"]

        detail = client.get(f"/api/tickets/{ticket_id}")
        assert detail.status_code == 200
        body = detail.json()
        assert body["draft_text"] == "Edited draft for the customer."
        assert body["risk_flags"] == ["chargeback"]
        assert body["sources"][0]["id"] == "missing-chunk"
        assert body["sources"][0]["title"] is None
        assert body["sources"][0]["excerpt"] is None
        assert body["assigned_to"] == me["id"]

        audit = client.get(f"/api/tickets/{ticket_id}/audit")
        assert audit.status_code == 200
        event_types = [item["event_type"] for item in audit.json()["items"]]
        assert "ticket.draft_saved" in event_types
        assert "ticket.escalated" in event_types
    finally:
        _cleanup(ticket_id)


def test_draft_creates_stub_run_before_classification(client: TestClient) -> None:
    ticket_id = _seed_ticket(with_run=False)
    try:
        _login(client)
        detail = client.get(f"/api/tickets/{ticket_id}")
        assert detail.status_code == 200
        assert detail.json()["draft_text"] is None
        assert detail.json()["risk_flags"] is None
        assert detail.json()["sources"] is None

        saved = client.patch(
            f"/api/tickets/{ticket_id}/draft",
            json={"body": "Wrote this before the bot finished."},
        )
        assert saved.status_code == 200, saved.text
        again = client.get(f"/api/tickets/{ticket_id}")
        assert again.json()["draft_text"] == "Wrote this before the bot finished."
        assert again.json()["risk_flags"] == []
        assert again.json()["sources"] == []
    finally:
        _cleanup(ticket_id)
