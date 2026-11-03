from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.models.enums import TicketStatus

if TYPE_CHECKING:
    from app.db.models.ai_run import AiRun
    from app.db.models.audit import AuditEvent
    from app.db.models.message import Message
    from app.db.models.send_attempt import SendAttempt
    from app.db.models.user import User


class Ticket(Base):
    __tablename__ = "tickets"
    __table_args__ = (
        CheckConstraint(
            "status IN ('new', 'processing', 'needs_review', 'approved', "
            "'replied', 'auto_replied', 'escalated', 'resolved', 'failed')",
            name="ck_tickets_status",
        ),
        CheckConstraint(
            "category IS NULL OR category IN ("
            "'order_status', 'shipping', 'returns', 'refund', "
            "'product_question', 'damaged_item', 'missing_item', "
            "'payment', 'complaint', 'other')",
            name="ck_tickets_category",
        ),
        CheckConstraint(
            "priority IS NULL OR priority IN ('low', 'medium', 'high', 'urgent')",
            name="ck_tickets_priority",
        ),
        Index("ix_tickets_status_category", "status", "category"),
        Index("ix_tickets_last_message_at", "last_message_at"),
        Index("ix_tickets_customer_email", "customer_email"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    gmail_thread_id: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    customer_email: Mapped[str] = mapped_column(String(320), nullable=False)
    subject: Mapped[str | None] = mapped_column(String(998))
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=TicketStatus.NEW.value,
        index=True,
    )
    category: Mapped[str | None] = mapped_column(String(64), index=True)
    priority: Mapped[str | None] = mapped_column(String(32))
    assigned_to: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
    )
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
    last_message_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    assignee: Mapped[User | None] = relationship(back_populates="assigned_tickets")
    messages: Mapped[list[Message]] = relationship(
        back_populates="ticket",
        passive_deletes=True,
    )
    ai_runs: Mapped[list[AiRun]] = relationship(
        back_populates="ticket",
        passive_deletes=True,
    )
    send_attempts: Mapped[list[SendAttempt]] = relationship(
        back_populates="ticket",
        passive_deletes=True,
    )
    audit_events: Mapped[list[AuditEvent]] = relationship(back_populates="ticket")
