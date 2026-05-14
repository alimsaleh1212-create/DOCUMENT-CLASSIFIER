"""Add comment/comment_color to predictions; expand audit action constraint.

Revision ID: 0002_prediction_comments
Revises: 0001_initial
Create Date: 2026-05-14
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0002_prediction_comments"
down_revision: str | None = "0001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Add comment columns to predictions
    op.add_column("predictions", sa.Column("comment", sa.String(length=2000), nullable=True))
    op.add_column("predictions", sa.Column("comment_color", sa.String(length=20), nullable=True))

    # Expand the audit_log action check constraint to include new actions
    op.drop_constraint("ck_audit_log_action_valid", "audit_log")
    op.create_check_constraint(
        "ck_audit_log_action_valid",
        "audit_log",
        "action IN ('role_change', 'relabel', 'batch_state', 'add_comment', 'delete_user')",
    )

    # Seed new Casbin permissions (idempotent via INSERT … ON CONFLICT DO NOTHING)
    op.execute(
        """
        INSERT INTO casbin_rule (ptype, v0, v1, v2)
        VALUES
            ('p', 'admin',    'delete_user',   'allow'),
            ('p', 'admin',    'add_comment',   'allow'),
            ('p', 'admin',    'trigger_scan',  'allow'),
            ('p', 'reviewer', 'add_comment',   'allow'),
            ('p', 'reviewer', 'trigger_scan',  'allow')
        ON CONFLICT DO NOTHING
        """
    )


def downgrade() -> None:
    op.drop_column("predictions", "comment_color")
    op.drop_column("predictions", "comment")

    op.drop_constraint("ck_audit_log_action_valid", "audit_log")
    op.create_check_constraint(
        "ck_audit_log_action_valid",
        "audit_log",
        "action IN ('role_change', 'relabel', 'batch_state')",
    )
