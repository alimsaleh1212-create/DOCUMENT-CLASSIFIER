"""Add document_name to predictions; expand audit action constraint; seed rename_document permission.

Revision ID: 0004_document_name
Revises: 0003_prediction_latency
Create Date: 2026-05-14
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0004_document_name"
down_revision: str | None = "0003_prediction_latency"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "predictions", sa.Column("document_name", sa.String(length=255), nullable=True)
    )

    op.drop_constraint("ck_audit_log_action_valid", "audit_log")
    op.create_check_constraint(
        "ck_audit_log_action_valid",
        "audit_log",
        "action IN ('role_change', 'relabel', 'batch_state', 'add_comment', 'delete_user', 'rename_document')",
    )

    op.execute(
        """
        INSERT INTO casbin_rule (ptype, v0, v1, v2)
        VALUES
            ('p', 'admin',    'rename_document', 'allow'),
            ('p', 'reviewer', 'rename_document', 'allow')
        ON CONFLICT DO NOTHING
        """
    )


def downgrade() -> None:
    op.drop_column("predictions", "document_name")

    op.drop_constraint("ck_audit_log_action_valid", "audit_log")
    op.create_check_constraint(
        "ck_audit_log_action_valid",
        "audit_log",
        "action IN ('role_change', 'relabel', 'batch_state', 'add_comment', 'delete_user')",
    )
