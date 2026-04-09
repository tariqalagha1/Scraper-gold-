"""Add run telemetry fields for compression and stealth tracking.

Revision ID: 20260408_0005
Revises: 20260329_0004
Create Date: 2026-04-08 12:20:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260408_0005"
down_revision = "20260329_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("runs", sa.Column("token_compression_ratio", sa.Float(), nullable=True))
    op.add_column(
        "runs",
        sa.Column("stealth_engaged", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column("runs", sa.Column("markdown_snapshot_path", sa.String(length=500), nullable=True))


def downgrade() -> None:
    op.drop_column("runs", "markdown_snapshot_path")
    op.drop_column("runs", "stealth_engaged")
    op.drop_column("runs", "token_compression_ratio")
