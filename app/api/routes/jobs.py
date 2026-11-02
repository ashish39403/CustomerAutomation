from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, require_admin
from app.db.models import Job, User
from app.db.session import get_db
from app.modules.jobs.queue import retry_dead_job

router = APIRouter(prefix="/jobs", tags=["jobs"])


class JobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    job_type: str
    status: str
    attempts: int
    max_attempts: int
    payload_json: dict
    last_error: str | None
    available_at: datetime
    locked_by: str | None
    locked_until: datetime | None
    created_at: datetime
    updated_at: datetime


class JobListResponse(BaseModel):
    items: list[JobResponse]
    total: int


@router.get("", response_model=JobListResponse)
def list_jobs(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
    status: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> JobListResponse:
    query = select(Job).order_by(Job.created_at.desc())
    if status:
        query = query.where(Job.status == status)
    rows = db.scalars(query.offset(offset).limit(limit)).all()
    count_query = select(func.count()).select_from(Job)
    if status:
        count_query = count_query.where(Job.status == status)
    total = db.scalar(count_query) or 0
    return JobListResponse(items=[JobResponse.model_validate(row) for row in rows], total=total)


@router.post("/{job_id}/retry", response_model=JobResponse)
def retry_job(
    job_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
) -> JobResponse:
    job = retry_dead_job(db, job_id, actor_id=user.id)
    return JobResponse.model_validate(job)
