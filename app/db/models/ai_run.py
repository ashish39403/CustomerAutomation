from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.message import Message
    from app.db.models.send_attempt import SendAttempt
    from app.db.models.ticket import Ticket


class AiRun(Base):
    __tablename__ = "ai_runs"
    __table_args__ = (
        Index("ix_ai_runs_ticket_id", "ticket_id"),
        Index("ix_ai_runs_message_id", "message_id"),
        Index("ix_ai_runs_created_at", "created_at"),
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
    message_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("messages.id", ondelete="SET NULL"),
    )
    model: Mapped[str | None] = mapped_column(String(128))
    prompt_version: Mapped[str | None] = mapped_column(String(64))
    pipeline_version: Mapped[str | None] = mapped_column(String(64))
    classification_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    risk_flags_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    retrieved_chunk_ids: Mapped[list[str] | None] = mapped_column(JSONB)
    draft_text: Mapped[str | None] = mapped_column(Text)
    decision: Mapped[str | None] = mapped_column(String(64), index=True)
    decision_reason: Mapped[str | None] = mapped_column(Text)
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    token_usage_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    ticket: Mapped[Ticket] = relationship(back_populates="ai_runs")
    message: Mapped[Message | None] = relationship(back_populates="ai_runs")
    send_attempts: Mapped[list[SendAttempt]] = relationship(back_populates="ai_run")
