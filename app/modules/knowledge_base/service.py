from __future__ import annotations

import hashlib
import os
import uuid
from pathlib import Path

import structlog
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import AppError, NotFoundError
from app.db.models import Document
from app.db.models.enums import DocumentStatus, JobType
from app.modules.jobs.queue import enqueue
from app.modules.knowledge_base.extraction import ALLOWED_EXTENSIONS, ALLOWED_MIME
from app.modules.knowledge_base.storage import put_bytes

log = structlog.get_logger("kb")
SKIP_SEED = {"KNOWLEDGE_MANIFEST.md"}


def upload_document(
    db: Session,
    *,
    filename: str,
    content_type: str | None,
    data: bytes,
    uploaded_by: uuid.UUID | None,
    replace_id: uuid.UUID | None = None,
) -> Document:
    suffix = Path(filename).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise AppError("Only PDF, TXT, and Markdown are allowed", status_code=400, code="invalid_file")
    if content_type and content_type.split(";")[0].strip() not in ALLOWED_MIME:
        raise AppError("Unsupported content type", status_code=400, code="invalid_file")
    if len(data) > settings.max_upload_bytes:
        raise AppError("File too large", status_code=400, code="invalid_file")

    checksum = hashlib.sha256(data).hexdigest()
    document = db.get(Document, replace_id) if replace_id else None
    if replace_id and document is None:
        raise NotFoundError("Document not found")
    object_key = document.object_key if document else f"kb/{uuid.uuid4().hex}/{Path(filename).name}"
    put_bytes(object_key, data, content_type=content_type)
    if document is None:
        document = Document(
            title=Path(filename).stem,
            object_key=object_key,
            mime_type=content_type or "application/octet-stream",
            size_bytes=len(data),
            checksum=checksum,
            version=1,
            status=DocumentStatus.QUEUED.value,
            uploaded_by=uploaded_by,
        )
        db.add(document)
        db.flush()
    else:
        document.title = Path(filename).stem
        document.mime_type = content_type or document.mime_type
        document.size_bytes = len(data)
        document.checksum = checksum
        document.version += 1
        document.status = DocumentStatus.QUEUED.value
        document.indexed_at = None
    enqueue(db, JobType.INDEX_DOCUMENT.value, {"document_id": str(document.id)})
    db.commit()
    db.refresh(document)
    log.info("kb.uploaded", document_id=str(document.id), version=document.version)
    return document


def queue_delete(db: Session, document_id: uuid.UUID) -> Document:
    document = db.get(Document, document_id)
    if document is None or document.status == DocumentStatus.DELETED.value:
        raise NotFoundError("Document not found")
    document.status = DocumentStatus.DELETING.value
    enqueue(db, JobType.DELETE_DOCUMENT.value, {"document_id": str(document.id)})
    db.commit()
    db.refresh(document)
    return document


def seed_knowledge_docs(db: Session) -> int:
    if os.environ.get("PYTEST_VERSION"):
        return 0
    root = Path(settings.knowledge_docs_dir)
    if not root.is_dir():
        return 0
    queued = 0
    for path in sorted(root.glob("*")):
        if not path.is_file() or path.name in SKIP_SEED:
            continue
        if path.suffix.lower() not in ALLOWED_EXTENSIONS:
            continue
        data = path.read_bytes()
        checksum = hashlib.sha256(data).hexdigest()
        object_key = f"kb/seed/{path.name}"
        put_bytes(object_key, data, content_type="text/markdown")
        existing = db.scalar(select(Document).where(Document.object_key == object_key))
        if existing and existing.checksum == checksum and existing.status == DocumentStatus.INDEXED.value:
            continue
        if existing is None:
            existing = Document(
                title=path.stem,
                object_key=object_key,
                mime_type="text/markdown",
                size_bytes=len(data),
                checksum=checksum,
                version=1,
                status=DocumentStatus.QUEUED.value,
            )
            db.add(existing)
            db.flush()
        else:
            existing.checksum = checksum
            existing.size_bytes = len(data)
            existing.version += 1
            existing.status = DocumentStatus.QUEUED.value
        enqueue(db, JobType.INDEX_DOCUMENT.value, {"document_id": str(existing.id)})
        queued += 1
    if queued:
        db.commit()
        log.info("kb.seed_queued", count=queued)
    return queued
