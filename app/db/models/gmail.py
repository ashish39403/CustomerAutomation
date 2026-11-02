from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.models.enums import GmailAccountStatus


class GmailAccount(Base):
    __tablename__ = "gmail_accounts"
    __table_args__ = (
        CheckConstraint(
            "status IN ('connected', 'expired', 'needs_reauthorization', 'disconnected')",
            name="ck_gmail_accounts_status",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False)
    encrypted_refresh_token: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default=GmailAccountStatus.NEEDS_REAUTHORIZATION.value,
    )
    scopes: Mapped[str | None] = mapped_column(Text)
    history_id: Mapped[str | None] = mapped_column(String(64))
    last_history_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
