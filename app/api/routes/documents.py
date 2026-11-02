from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, UploadFile
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, require_admin
from app.db.models import Document, User
from app.db.session import get_db
from app.modules.knowledge_base.service import queue_delete, upload_document

router = APIRouter(prefix="/documents", tags=["documents"])


class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    object_key: str
    mime_type: str
    size_bytes: int
    checksum: str | None
    version: int
    status: str
    created_at: datetime
    indexed_at: datetime | None


class DocumentListResponse(BaseModel):
    items: list[DocumentResponse]


@router.get("", response_model=DocumentListResponse)
def list_documents(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> DocumentListResponse:
    rows = db.scalars(select(Document).order_by(Document.created_at.desc())).all()
    return DocumentListResponse(items=[DocumentResponse.model_validate(row) for row in rows])


@router.post("", response_model=DocumentResponse)
async def create_document(
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
    file: UploadFile = File(...),
    replace_id: UUID | None = Form(default=None),
) -> DocumentResponse:
    data = await file.read()
    document = upload_document(
        db,
        filename=file.filename or "upload.bin",
        content_type=file.content_type,
        data=data,
        uploaded_by=user.id,
        replace_id=replace_id,
    )
    return DocumentResponse.model_validate(document)


@router.delete("/{document_id}", response_model=DocumentResponse)
def delete_document(
    document_id: UUID,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> DocumentResponse:
    document = queue_delete(db, document_id)
    return DocumentResponse.model_validate(document)
