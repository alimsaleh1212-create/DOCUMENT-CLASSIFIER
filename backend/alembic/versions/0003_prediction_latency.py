"""Add latency_ms column to predictions.

Revision ID: 0003_prediction_latency
Revises: 0002_prediction_comments
Create Date: 2026-05-14
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0003_prediction_latency"
down_revision: str | None = "0002_prediction_comments"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("predictions", sa.Column("latency_ms", sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column("predictions", "latency_ms")
