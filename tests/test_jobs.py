from __future__ import annotations

import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from app.core.config import settings
from app.db.models import Job
from app.db.models.enums import JobStatus
from app.db.session import SessionLocal
from app.modules.jobs.errors import PermanentJobError
from app.modules.jobs.handlers import run_handler
from app.modules.jobs.queue import ClaimedJob, claim, enqueue, reap_expired_leases, retry_dead_job


def _insert_job(job_type: str = "test.noop") -> uuid.UUID:
    with SessionLocal() as db:
        job = enqueue(db, job_type, {"marker": str(uuid.uuid4())})
        db.commit()
        return job.id


def _delete_job(job_id: uuid.UUID) -> None:
    with SessionLocal() as db:
        job = db.get(Job, job_id)
        if job is not None:
            db.delete(job)
            db.commit()


def test_two_workers_cannot_claim_the_same_job() -> None:
    job_id = _insert_job()
    try:
        results: list[str | None] = []

        def take() -> str | None:
            claimed = claim(f"w-{uuid.uuid4().hex[:6]}")
            return str(claimed.id) if claimed else None

        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(take) for _ in range(2)]
            for future in as_completed(futures):
                results.append(future.result())

        assert results.count(str(job_id)) == 1
        assert results.count(None) == 1
    finally:
        _delete_job(job_id)


def test_reaper_recovers_expired_lease() -> None:
    job_id = _insert_job()
    try:
        with SessionLocal() as db:
            job = db.get(Job, job_id)
            assert job is not None
            job.status = JobStatus.RUNNING.value
            job.locked_by = "crashed-worker"
            job.locked_until = datetime.now(UTC) - timedelta(seconds=5)
            job.attempts = 1
            db.commit()
        assert reap_expired_leases() >= 1
        with SessionLocal() as db:
            job = db.get(Job, job_id)
            assert job is not None
            assert job.status == JobStatus.RETRY_WAIT.value
            assert job.locked_by is None
    finally:
        _delete_job(job_id)


def test_retry_dead_job_is_queued_once() -> None:
    job_id = _insert_job()
    try:
        with SessionLocal() as db:
            job = db.get(Job, job_id)
            assert job is not None
            job.status = JobStatus.DEAD.value
            db.commit()
        with SessionLocal() as db:
            retry_dead_job(db, job_id, actor_id=None)
        with SessionLocal() as db:
            job = db.get(Job, job_id)
            assert job is not None
            assert job.status == JobStatus.QUEUED.value
    finally:
        _delete_job(job_id)


def test_unknown_job_type_is_permanent() -> None:
    with SessionLocal() as db:
        try:
            run_handler(
                db,
                ClaimedJob(
                    id=uuid.uuid4(),
                    job_type="not.a.handler",
                    payload={},
                    attempts=1,
                    max_attempts=5,
                ),
            )
        except PermanentJobError as exc:
            assert "unknown job_type" in str(exc)
        else:
            raise AssertionError("expected PermanentJobError")


def test_admin_can_list_and_retry_dead_job(client: TestClient) -> None:
    job_id = _insert_job()
    try:
        with SessionLocal() as db:
            job = db.get(Job, job_id)
            assert job is not None
            job.status = JobStatus.DEAD.value
            db.commit()
        login = client.post(
            "/api/auth/login",
            json={"email": settings.dashboard_username, "password": settings.dashboard_password},
        )
        assert login.status_code == 200
        listed = client.get("/api/jobs", params={"status": "dead"})
        assert listed.status_code == 200
        assert any(item["id"] == str(job_id) for item in listed.json()["items"])
        retried = client.post(f"/api/jobs/{job_id}/retry")
        assert retried.status_code == 200
        assert retried.json()["status"] == JobStatus.QUEUED.value
    finally:
        _delete_job(job_id)
