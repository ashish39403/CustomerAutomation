from __future__ import annotations

from collections.abc import Callable
from typing import Any

import structlog
from sqlalchemy.orm import Session

from app.db.models.enums import JobType
from app.modules.jobs.errors import PermanentJobError, TransientJobError
from app.modules.jobs.queue import ClaimedJob

log = structlog.get_logger("jobs")

Handler = Callable[[Session, dict[str, Any]], None]


def handle_process_email(db: Session, payload: dict[str, Any]) -> None:
    from app.modules.ai.pipeline import process_email

    ticket_id = payload.get("ticket_id")
    message_id = payload.get("message_id")
    if not ticket_id or not message_id:
        raise PermanentJobError("process_email missing ticket_id or message_id")
    process_email(db, ticket_id, message_id)


def handle_poll_gmail(db: Session, payload: dict[str, Any]) -> None:
    from app.modules.gmail.poller import poll_account

    account_id = payload.get("gmail_account_id")
    if not account_id:
        raise PermanentJobError("poll_gmail missing gmail_account_id")
    poll_account(db, account_id)


def handle_index_document(db: Session, payload: dict[str, Any]) -> None:
    from app.modules.knowledge_base.indexer import index_document

    document_id = payload.get("document_id")
    if not document_id:
        raise PermanentJobError("index_document missing document_id")
    index_document(db, document_id)


def handle_delete_document(db: Session, payload: dict[str, Any]) -> None:
    from app.modules.knowledge_base.indexer import delete_document

    document_id = payload.get("document_id")
    if not document_id:
        raise PermanentJobError("delete_document missing document_id")
    delete_document(db, document_id)


HANDLERS: dict[str, Handler] = {
    JobType.PROCESS_EMAIL.value: handle_process_email,
    JobType.POLL_GMAIL.value: handle_poll_gmail,
    JobType.INDEX_DOCUMENT.value: handle_index_document,
    JobType.DELETE_DOCUMENT.value: handle_delete_document,
}


def run_handler(db: Session, job: ClaimedJob) -> None:
    handler = HANDLERS.get(job.job_type)
    if handler is None:
        raise PermanentJobError(f"unknown job_type {job.job_type}")
    try:
        handler(db, job.payload)
    except (TransientJobError, PermanentJobError):
        raise
    except Exception as exc:
        raise TransientJobError(str(exc)) from exc
