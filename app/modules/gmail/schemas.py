from datetime import datetime

from pydantic import BaseModel, Field


class AttachmentMeta(BaseModel):
    filename: str | None = None
    mime_type: str | None = None
    size: int | None = None


class NormalizedEmail(BaseModel):
    gmail_message_id: str
    gmail_thread_id: str
    from_email: str
    to_emails: list[str] = Field(default_factory=list)
    subject: str | None = None
    body_text: str | None = None
    received_at: datetime | None = None
    headers: dict[str, str] = Field(default_factory=dict)
    attachments: list[AttachmentMeta] = Field(default_factory=list)


class SkipReason(BaseModel):
    code: str
    detail: str
