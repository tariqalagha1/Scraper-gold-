"""Add run execution contract and result snapshots.

Revision ID: 20260507_0008
Revises: 20260504_0007
Create Date: 2026-05-07 12:00:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260507_0008"
down_revision = "20260504_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("runs", sa.Column("execution_contract", sa.JSON(), nullable=True))
    op.add_column("runs", sa.Column("execution_result", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("runs", "execution_result")
    op.drop_column("runs", "execution_contract")
