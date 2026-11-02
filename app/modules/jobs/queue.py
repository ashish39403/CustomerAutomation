from __future__ import annotations

import random
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

import structlog
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import AuditEvent, Job
from app.db.models.enums import ActorType, JobStatus
from app.db.session import SessionLocal

log = structlog.get_logger("jobs")

CLAIMABLE = (JobStatus.QUEUED.value, JobStatus.RETRY_WAIT.value)


@dataclass(frozen=True, slots=True)
class ClaimedJob:
    id: uuid.UUID
    job_type: str
    payload: dict[str, Any]
    attempts: int
    max_attempts: int


def enqueue(
    db: Session,
    job_type: str,
    payload: dict[str, Any],
    *,
    available_at: datetime | None = None,
    max_attempts: int = 5,
) -> Job:
    job = Job(
        job_type=job_type,
        payload_json=payload,
        status=JobStatus.QUEUED.value,
        available_at=available_at or datetime.now(UTC),
        max_attempts=max_attempts,
    )
    db.add(job)
    db.flush()
    log.info("jobs.enqueued", job_id=str(job.id), job_type=job_type)
    return job


def claim(worker_id: str) -> ClaimedJob | None:
    now = datetime.now(UTC)
    with SessionLocal() as db:
        job = db.scalar(
            select(Job)
            .where(Job.status.in_(CLAIMABLE), Job.available_at <= now)
            .order_by(Job.available_at, Job.created_at)
            .with_for_update(skip_locked=True)
            .limit(1)
        )
        if job is None:
            return None
        job.status = JobStatus.RUNNING.value
        job.locked_by = worker_id
        job.locked_until = now + timedelta(seconds=settings.job_lease_seconds)
        job.attempts += 1
        job.updated_at = now
        db.commit()
        log.info(
            "jobs.claimed",
            job_id=str(job.id),
            job_type=job.job_type,
            attempts=job.attempts,
            worker_id=worker_id,
        )
        return ClaimedJob(
            id=job.id,
            job_type=job.job_type,
            payload=dict(job.payload_json or {}),
            attempts=job.attempts,
            max_attempts=job.max_attempts,
        )


def mark_succeeded(job_id: uuid.UUID) -> None:
    _set_status(job_id, JobStatus.SUCCEEDED, clear_lock=True)


def mark_dead(job_id: uuid.UUID, error: str) -> None:
    _set_status(job_id, JobStatus.DEAD, error=error, clear_lock=True)
    log.warning("jobs.dead", job_id=str(job_id), error=error)


def schedule_retry(job_id: uuid.UUID, error: str, attempts: int, max_attempts: int) -> None:
    if attempts >= max_attempts:
        mark_dead(job_id, error)
        return
    delay = min(2 ** max(attempts - 1, 0), 300) + random.uniform(0, 1)
    available_at = datetime.now(UTC) + timedelta(seconds=delay)
    with SessionLocal() as db:
        job = db.get(Job, job_id)
        if job is None:
            return
        job.status = JobStatus.RETRY_WAIT.value
        job.last_error = error[:4000]
        job.available_at = available_at
        job.locked_by = None
        job.locked_until = None
        job.updated_at = datetime.now(UTC)
        db.commit()
    log.info("jobs.retry_wait", job_id=str(job_id), delay_seconds=round(delay, 2), error=error)


def reap_expired_leases() -> int:
    now = datetime.now(UTC)
    with SessionLocal() as db:
        expired = db.scalars(
            select(Job).where(
                Job.status == JobStatus.RUNNING.value,
                Job.locked_until.is_not(None),
                Job.locked_until < now,
            )
        ).all()
        count = 0
        for job in expired:
            if job.attempts >= job.max_attempts:
                job.status = JobStatus.DEAD.value
            else:
                delay = min(2 ** max(job.attempts - 1, 0), 300)
                job.status = JobStatus.RETRY_WAIT.value
                job.available_at = now + timedelta(seconds=delay)
            job.locked_by = None
            job.locked_until = None
            job.last_error = (job.last_error or "") + "\nlease expired"
            job.updated_at = now
            count += 1
            log.warning("jobs.lease_expired", job_id=str(job.id), attempts=job.attempts)
        if count:
            db.commit()
        return count


def retry_dead_job(db: Session, job_id: uuid.UUID, *, actor_id: uuid.UUID | None) -> Job:
    job = db.get(Job, job_id)
    if job is None:
        from app.core.errors import NotFoundError

        raise NotFoundError("Job not found")
    if job.status != JobStatus.DEAD.value:
        from app.core.errors import ConflictError

        raise ConflictError("Only dead jobs can be retried")
    job.status = JobStatus.QUEUED.value
    job.available_at = datetime.now(UTC)
    job.locked_by = None
    job.locked_until = None
    job.last_error = None
    job.updated_at = datetime.now(UTC)
    db.add(
        AuditEvent(
            actor_type=ActorType.USER.value,
            actor_id=actor_id,
            event_type="job.retried",
            event_data_json={"job_id": str(job.id), "job_type": job.job_type},
        )
    )
    db.commit()
    db.refresh(job)
    log.info("jobs.retried", job_id=str(job.id), actor_id=str(actor_id) if actor_id else None)
    return job


def _set_status(
    job_id: uuid.UUID,
    status: JobStatus,
    *,
    error: str | None = None,
    clear_lock: bool = False,
) -> None:
    values: dict[str, Any] = {"status": status.value, "updated_at": datetime.now(UTC)}
    if error is not None:
        values["last_error"] = error[:4000]
    if clear_lock:
        values["locked_by"] = None
        values["locked_until"] = None
    with SessionLocal() as db:
        db.execute(update(Job).where(Job.id == job_id).values(**values))
        db.commit()
