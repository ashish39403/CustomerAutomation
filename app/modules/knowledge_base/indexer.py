from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

import structlog
from qdrant_client.models import PointStruct
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.db.models import AuditEvent, Document, DocumentChunk
from app.db.models.enums import ActorType, DocumentStatus
from app.modules.jobs.errors import PermanentJobError, TransientJobError
from app.modules.knowledge_base.chunking import chunk_document
from app.modules.knowledge_base.embeddings import embed_texts
from app.modules.knowledge_base.extraction import extract_text
from app.modules.knowledge_base.qdrant import delete_document_points, point_id, upsert_points
from app.modules.knowledge_base.storage import get_bytes

log = structlog.get_logger("kb")


def index_document(db: Session, document_id: str) -> None:
    document = db.get(Document, UUID(document_id))
    if document is None or document.status == DocumentStatus.DELETED.value:
        raise PermanentJobError("document missing")
    document.status = DocumentStatus.PROCESSING.value
    db.flush()
    try:
        raw = get_bytes(document.object_key)
        filename = document.object_key.rsplit("/", 1)[-1]
        meta, text = extract_text(raw, filename)
        if not text.strip():
            raise PermanentJobError("document has no extractable text")
        title = str(meta.get("title") or document.title)
        chunks = chunk_document(text, title=title)
        vectors = embed_texts([chunk.text for chunk in chunks])
        previous = [
            row
            for row in db.scalars(
                select(DocumentChunk).where(DocumentChunk.document_id == document.id)
            ).all()
            if row.document_version != document.version
        ]
        db.execute(
            delete(DocumentChunk).where(
                DocumentChunk.document_id == document.id,
                DocumentChunk.document_version == document.version,
            )
        )
        points: list[PointStruct] = []
        for chunk, vector in zip(chunks, vectors, strict=True):
            qid = point_id(document.id, document.version, chunk.index)
            row = DocumentChunk(
                document_id=document.id,
                document_version=document.version,
                chunk_index=chunk.index,
                content_hash=chunk.content_hash,
                source_locator=chunk.source_locator,
                qdrant_point_id=qid,
            )
            db.add(row)
            db.flush()
            points.append(
                PointStruct(
                    id=qid,
                    vector=vector,
                    payload={
                        "document_id": str(document.id),
                        "document_version": document.version,
                        "chunk_id": str(row.id),
                        "chunk_index": chunk.index,
                        "title": title,
                        "source": filename,
                        "source_locator": chunk.source_locator,
                        "document_type": str(meta.get("document_type") or ""),
                        "approved_category": str(meta.get("approved_category") or ""),
                        "active": True,
                        "text": chunk.text,
                    },
                )
            )
        upsert_points(points)
        old_versions = {row.document_version for row in previous}
        for version in old_versions:
            delete_document_points(document.id, version)
        for row in previous:
            db.delete(row)
        document.title = title
        document.status = DocumentStatus.INDEXED.value
        document.indexed_at = datetime.now(UTC)
        db.add(
            AuditEvent(
                actor_type=ActorType.SYSTEM.value,
                event_type="kb.indexed",
                event_data_json={"document_id": str(document.id), "chunks": len(chunks)},
            )
        )
        log.info("kb.indexed", document_id=str(document.id), chunks=len(chunks))
    except PermanentJobError:
        document.status = DocumentStatus.FAILED.value
        raise
    except Exception as exc:
        document.status = DocumentStatus.FAILED.value
        raise TransientJobError(str(exc)) from exc


def delete_document(db: Session, document_id: str) -> None:
    from app.modules.knowledge_base.storage import delete_bytes

    document = db.get(Document, UUID(document_id))
    if document is None:
        return
    document.status = DocumentStatus.DELETING.value
    db.flush()
    delete_document_points(document.id)
    delete_bytes(document.object_key)
    db.execute(delete(DocumentChunk).where(DocumentChunk.document_id == document.id))
    document.status = DocumentStatus.DELETED.value
    log.info("kb.deleted", document_id=str(document.id))
