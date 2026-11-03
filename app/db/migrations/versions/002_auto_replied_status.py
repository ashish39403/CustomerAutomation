"""Allow the auto_replied ticket status.

Revision ID: 002_auto_replied
Revises: 001_initial
Create Date: 2026-11-03
"""

from typing import Sequence, Union

from alembic import op

revision: str = "002_auto_replied"
down_revision: Union[str, Sequence[str], None] = "001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint("ck_tickets_status", "tickets", type_="check")
    op.create_check_constraint(
        "ck_tickets_status",
        "tickets",
        "status IN ('new', 'processing', 'needs_review', 'approved', "
        "'replied', 'auto_replied', 'escalated', 'resolved', 'failed')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_tickets_status", "tickets", type_="check")
    op.create_check_constraint(
        "ck_tickets_status",
        "tickets",
        "status IN ('new', 'processing', 'needs_review', 'approved', "
        "'replied', 'escalated', 'resolved', 'failed')",
    )
