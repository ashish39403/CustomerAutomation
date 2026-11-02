from __future__ import annotations

import signal
import socket
import time
import uuid
from datetime import UTC, datetime, timedelta

import structlog
from sqlalchemy import select

from app.core.config import settings
from app.core.logging import configure_logging
from app.db.models import GmailAccount, Job
from app.db.models.enums import GmailAccountStatus, JobStatus, JobType
from app.db.session import SessionLocal
from app.modules.jobs.errors import PermanentJobError, TransientJobError
from app.modules.jobs.handlers import run_handler
from app.modules.jobs.queue import claim, enqueue, mark_dead, mark_succeeded, reap_expired_leases, schedule_retry

log = structlog.get_logger("worker")
_stop = False


def _handle_stop(_signum: int, _frame: object) -> None:
    global _stop
    _stop = True


def process_one(worker_id: str) -> bool:
    job = claim(worker_id)
    if job is None:
        return False
    try:
        with SessionLocal() as db:
            run_handler(db, job)
            db.commit()
        mark_succeeded(job.id)
    except PermanentJobError as exc:
        mark_dead(job.id, str(exc))
    except TransientJobError as exc:
        schedule_retry(job.id, str(exc), job.attempts, job.max_attempts)
    return True


def enqueue_poll_if_due() -> None:
    with SessionLocal() as db:
        account = db.scalar(
            select(GmailAccount).where(GmailAccount.status == GmailAccountStatus.CONNECTED.value)
        )
        if account is None:
            return
        pending = db.scalar(
            select(Job.id).where(
                Job.job_type == JobType.POLL_GMAIL.value,
                Job.status.in_(
                    (
                        JobStatus.QUEUED.value,
                        JobStatus.RUNNING.value,
                        JobStatus.RETRY_WAIT.value,
                    )
                ),
            )
        )
        if pending is not None:
            return
        due = account.last_history_sync_at is None or (
            datetime.now(UTC) - account.last_history_sync_at
            >= timedelta(seconds=settings.gmail_poll_interval_seconds)
        )
        if not due:
            return
        enqueue(db, JobType.POLL_GMAIL.value, {"gmail_account_id": str(account.id)})
        db.commit()


def tick(worker_id: str) -> bool:
    reap_expired_leases()
    enqueue_poll_if_due()
    return process_one(worker_id)


def main() -> None:
    configure_logging()
    worker_id = f"{socket.gethostname()}:{uuid.uuid4().hex[:8]}"
    signal.signal(signal.SIGINT, _handle_stop)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, _handle_stop)
    from app.modules.knowledge_base.service import seed_knowledge_docs

    with SessionLocal() as db:
        seed_knowledge_docs(db)
    log.info("worker.started", worker_id=worker_id, env=settings.app_env)
    while not _stop:
        worked = tick(worker_id)
        if not worked:
            time.sleep(settings.job_poll_interval_seconds)
    log.info("worker.stopped", worker_id=worker_id)
