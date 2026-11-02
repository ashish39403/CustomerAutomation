from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.models.enums import SendAttemptStatus

if TYPE_CHECKING:
    from app.db.models.ai_run import AiRun
    from app.db.models.ticket import Ticket


class SendAttempt(Base):
    __tablename__ = "send_attempts"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'sent', 'failed', 'unknown')",
            name="ck_send_attempts_status",
        ),
        Index("ix_send_attempts_ticket_id", "ticket_id"),
        Index("ix_send_attempts_status", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    ticket_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tickets.id", ondelete="CASCADE"),
        nullable=False,
    )
    ai_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ai_runs.id", ondelete="SET NULL"),
    )
    idempotency_key: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=SendAttemptStatus.PENDING.value,
    )
    gmail_message_id: Mapped[str | None] = mapped_column(String(128))
    attempted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error: Mapped[str | None] = mapped_column(Text)
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

    ticket: Mapped[Ticket] = relationship(back_populates="send_attempts")
    ai_run: Mapped[AiRun | None] = relationship(back_populates="send_attempts")
