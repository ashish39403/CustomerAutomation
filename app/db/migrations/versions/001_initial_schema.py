"""Initial operational schema.

Revision ID: 001_initial
Revises:
Create Date: 2026-11-02
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "001_initial"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("display_name", sa.String(length=120), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("role IN ('operator', 'admin')", name="ck_users_role"),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )

    op.create_table(
        "gmail_accounts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("encrypted_refresh_token", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("scopes", sa.Text(), nullable=True),
        sa.Column("history_id", sa.String(length=64), nullable=True),
        sa.Column("last_history_sync_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('connected', 'expired', 'needs_reauthorization', 'disconnected')",
            name="ck_gmail_accounts_status",
        ),
        sa.UniqueConstraint("email", name="uq_gmail_accounts_email"),
    )

    op.create_table(
        "tickets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("gmail_thread_id", sa.String(length=128), nullable=False),
        sa.Column("customer_email", sa.String(length=320), nullable=False),
        sa.Column("subject", sa.String(length=998), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("category", sa.String(length=64), nullable=True),
        sa.Column("priority", sa.String(length=32), nullable=True),
        sa.Column("assigned_to", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("last_message_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('new', 'processing', 'needs_review', 'approved', "
            "'replied', 'escalated', 'resolved', 'failed')",
            name="ck_tickets_status",
        ),
        sa.CheckConstraint(
            "category IS NULL OR category IN ("
            "'order_status', 'shipping', 'returns', 'refund', "
            "'product_question', 'damaged_item', 'missing_item', "
            "'payment', 'complaint', 'other')",
            name="ck_tickets_category",
        ),
        sa.CheckConstraint(
            "priority IS NULL OR priority IN ('low', 'medium', 'high', 'urgent')",
            name="ck_tickets_priority",
        ),
        sa.ForeignKeyConstraint(["assigned_to"], ["users.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("gmail_thread_id", name="uq_tickets_gmail_thread_id"),
    )
    op.create_index("ix_tickets_status", "tickets", ["status"])
    op.create_index("ix_tickets_category", "tickets", ["category"])
    op.create_index("ix_tickets_status_category", "tickets", ["status", "category"])
    op.create_index("ix_tickets_last_message_at", "tickets", ["last_message_at"])
    op.create_index("ix_tickets_customer_email", "tickets", ["customer_email"])

    op.create_table(
        "messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("ticket_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("gmail_message_id", sa.String(length=128), nullable=False),
        sa.Column("direction", sa.String(length=16), nullable=False),
        sa.Column("from_email", sa.String(length=320), nullable=False),
        sa.Column(
            "to_emails",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column("subject", sa.String(length=998), nullable=True),
        sa.Column("body_text", sa.Text(), nullable=True),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("headers_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "attachments_metadata_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "direction IN ('inbound', 'outbound')",
            name="ck_messages_direction",
        ),
        sa.ForeignKeyConstraint(["ticket_id"], ["tickets.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("gmail_message_id", name="uq_messages_gmail_message_id"),
    )
    op.create_index("ix_messages_ticket_id", "messages", ["ticket_id"])
    op.create_index("ix_messages_received_at", "messages", ["received_at"])

    op.create_table(
        "ai_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("ticket_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("message_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("model", sa.String(length=128), nullable=True),
        sa.Column("prompt_version", sa.String(length=64), nullable=True),
        sa.Column("pipeline_version", sa.String(length=64), nullable=True),
        sa.Column("classification_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("risk_flags_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("retrieved_chunk_ids", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("draft_text", sa.Text(), nullable=True),
        sa.Column("decision", sa.String(length=64), nullable=True),
        sa.Column("decision_reason", sa.Text(), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("token_usage_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["ticket_id"], ["tickets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["message_id"], ["messages.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_ai_runs_ticket_id", "ai_runs", ["ticket_id"])
    op.create_index("ix_ai_runs_message_id", "ai_runs", ["message_id"])
    op.create_index("ix_ai_runs_created_at", "ai_runs", ["created_at"])
    op.create_index("ix_ai_runs_decision", "ai_runs", ["decision"])

    op.create_table(
        "documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("title", sa.String(length=512), nullable=False),
        sa.Column("object_key", sa.String(length=1024), nullable=False),
        sa.Column("mime_type", sa.String(length=128), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("checksum", sa.String(length=128), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("uploaded_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("indexed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('uploaded', 'queued', 'processing', 'indexed', "
            "'failed', 'deleting', 'deleted')",
            name="ck_documents_status",
        ),
        sa.ForeignKeyConstraint(["uploaded_by"], ["users.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("object_key", name="uq_documents_object_key"),
    )
    op.create_index("ix_documents_status", "documents", ["status"])

    op.create_table(
        "document_chunks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_version", sa.Integer(), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("content_hash", sa.String(length=128), nullable=True),
        sa.Column("source_locator", sa.String(length=512), nullable=True),
        sa.Column("qdrant_point_id", sa.String(length=128), nullable=True),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.UniqueConstraint(
            "document_id",
            "document_version",
            "chunk_index",
            name="uq_document_chunks_version_index",
        ),
    )
    op.create_index("ix_document_chunks_qdrant_point_id", "document_chunks", ["qdrant_point_id"])
    op.create_index("ix_document_chunks_document_id", "document_chunks", ["document_id"])

    op.create_table(
        "jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("job_type", sa.String(length=64), nullable=False),
        sa.Column(
            "payload_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_attempts", sa.Integer(), nullable=False, server_default="5"),
        sa.Column(
            "available_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("locked_by", sa.String(length=128), nullable=True),
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('queued', 'running', 'succeeded', 'retry_wait', 'dead')",
            name="ck_jobs_status",
        ),
    )
    op.create_index("ix_jobs_status", "jobs", ["status"])
    op.create_index("ix_jobs_job_type", "jobs", ["job_type"])
    op.create_index("ix_jobs_available_at", "jobs", ["available_at"])
    op.create_index("ix_jobs_claim", "jobs", ["status", "available_at"])

    op.create_table(
        "send_attempts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("ticket_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ai_run_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("gmail_message_id", sa.String(length=128), nullable=True),
        sa.Column("attempted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'sent', 'failed', 'unknown')",
            name="ck_send_attempts_status",
        ),
        sa.ForeignKeyConstraint(["ticket_id"], ["tickets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["ai_run_id"], ["ai_runs.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("idempotency_key", name="uq_send_attempts_idempotency_key"),
    )
    op.create_index("ix_send_attempts_ticket_id", "send_attempts", ["ticket_id"])
    op.create_index("ix_send_attempts_status", "send_attempts", ["status"])

    op.create_table(
        "audit_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("actor_type", sa.String(length=32), nullable=False),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("ticket_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("event_data_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["ticket_id"], ["tickets.id"], ondelete="SET NULL"),
    )
    op.create_index(
        "ix_audit_events_ticket_id_created",
        "audit_events",
        ["ticket_id", "created_at"],
    )
    op.create_index("ix_audit_events_created_at", "audit_events", ["created_at"])
    op.create_index("ix_audit_events_event_type", "audit_events", ["event_type"])


def downgrade() -> None:
    op.drop_table("audit_events")
    op.drop_table("send_attempts")
    op.drop_table("jobs")
    op.drop_table("document_chunks")
    op.drop_table("documents")
    op.drop_table("ai_runs")
    op.drop_table("messages")
    op.drop_table("tickets")
    op.drop_table("gmail_accounts")
    op.drop_table("users")
