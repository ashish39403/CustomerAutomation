from __future__ import annotations

import time
from uuid import UUID

import structlog
from sqlalchemy.orm import Session

from app.db.models import AiRun, AuditEvent, Message, Ticket
from app.db.models.enums import ActorType, Decision, TicketStatus
from app.modules.ai.classifier import classify
from app.modules.ai.drafter import draft
from app.modules.ai.policy import decide, grounding_ok, overlay_risk_flags
from app.modules.ai.schemas import Classification
from app.modules.jobs.errors import PermanentJobError, TransientJobError
from app.modules.knowledge_base.retrieve import retrieve

log = structlog.get_logger("ai")
PIPELINE_VERSION = "v1"
PROMPT_VERSION = "v1"


def process_email(db: Session, ticket_id: str, message_id: str) -> None:
    ticket = db.get(Ticket, UUID(ticket_id))
    message = db.get(Message, UUID(message_id))
    if ticket is None or message is None:
        raise PermanentJobError("ticket or message missing")
    ticket.status = TicketStatus.PROCESSING.value
    started = time.perf_counter()
    try:
        _run(db, ticket, message, started)
    except PermanentJobError:
        ticket.status = TicketStatus.FAILED.value
        raise
    except Exception as exc:
        ticket.status = TicketStatus.FAILED.value
        raise TransientJobError(str(exc)) from exc


def _run(db: Session, ticket: Ticket, message: Message, started: float) -> None:
    email_text = f"Subject: {message.subject or ''}\n{message.body_text or ''}"
    try:
        classification = classify(
            subject=message.subject,
            from_email=message.from_email,
            body=message.body_text,
        )
    except Exception as exc:
        _store_run(
            db,
            ticket,
            message,
            started,
            classification=None,
            decision=Decision.ESCALATE,
            reason=f"classifier failed: {exc}",
            evidence=[],
            draft_text=None,
        )
        ticket.status = TicketStatus.FAILED.value
        log.warning("ai.classifier_failed", ticket_id=str(ticket.id), error=str(exc))
        return

    classification.risk_flags = overlay_risk_flags(email_text, classification.risk_flags)
    evidence: list[dict] = []
    draft_text = None
    cited: list[str] = []
    grounded = True
    skip_reply = False

    early_decision, early_reason = decide(
        classification, evidence_count=1, grounding_ok=True, skip_reply=skip_reply
    )
    needs_answer = early_decision == Decision.NEEDS_REVIEW

    if needs_answer or early_decision in {Decision.ESCALATE, Decision.INSUFFICIENT_EVIDENCE}:
        try:
            evidence = retrieve(f"{message.subject or ''}\n{message.body_text or ''}")
        except Exception as exc:
            log.warning("ai.retrieval_failed", ticket_id=str(ticket.id), error=str(exc))
            evidence = []

        evidence_text = "\n".join(item.get("text") or "" for item in evidence)
        draft_result = draft(
            classification=classification,
            email_text=email_text,
            evidence=evidence,
        )
        draft_text = draft_result.draft_text
        cited = draft_result.cited_chunk_ids
        if draft_result.insufficient_evidence or not evidence:
            grounded = False
        grounded = grounded and grounding_ok(draft_text, evidence_text)

    decision, reason = decide(
        classification,
        evidence_count=len(evidence),
        grounding_ok=grounded,
        skip_reply=skip_reply,
    )
    if decision == Decision.INSUFFICIENT_EVIDENCE:
        ticket.status = TicketStatus.ESCALATED.value
        ticket.category = classification.category.value
        ticket.priority = classification.priority.value
    elif decision == Decision.ESCALATE:
        ticket.status = TicketStatus.ESCALATED.value
        ticket.category = classification.category.value
        ticket.priority = classification.priority.value
    elif decision == Decision.NO_REPLY:
        ticket.status = TicketStatus.RESOLVED.value
    else:
        ticket.status = TicketStatus.NEEDS_REVIEW.value
        ticket.category = classification.category.value
        ticket.priority = classification.priority.value

    _store_run(
        db,
        ticket,
        message,
        started,
        classification=classification,
        decision=decision,
        reason=reason,
        evidence=evidence,
        draft_text=draft_text,
        cited=cited,
    )
    log.info(
        "ai.decision",
        ticket_id=str(ticket.id),
        decision=decision.value,
        reason=reason,
        category=classification.category.value,
        evidence=len(evidence),
    )


def _store_run(
    db: Session,
    ticket: Ticket,
    message: Message,
    started: float,
    *,
    classification: Classification | None,
    decision: Decision,
    reason: str,
    evidence: list[dict],
    draft_text: str | None,
    cited: list[str] | None = None,
) -> None:
    latency = int((time.perf_counter() - started) * 1000)
    run = AiRun(
        ticket_id=ticket.id,
        message_id=message.id,
        model=None if classification is None else "classifier+agent",
        prompt_version=PROMPT_VERSION,
        pipeline_version=PIPELINE_VERSION,
        classification_json=classification.model_dump(mode="json") if classification else None,
        risk_flags_json={"flags": classification.risk_flags} if classification else None,
        retrieved_chunk_ids=cited or [str(item.get("id")) for item in evidence],
        draft_text=draft_text,
        decision=decision.value,
        decision_reason=reason,
        latency_ms=latency,
    )
    db.add(run)
    db.add(
        AuditEvent(
            actor_type=ActorType.WORKER.value,
            ticket_id=ticket.id,
            event_type="ai.completed",
            event_data_json={
                "decision": decision.value,
                "reason": reason,
                "ticket_status": ticket.status,
            },
        )
    )
