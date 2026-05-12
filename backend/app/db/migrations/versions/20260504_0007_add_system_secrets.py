"""Add encrypted system secrets table.

Revision ID: 20260504_0007
Revises: 20260503_0006
Create Date: 2026-05-04 12:10:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260504_0007"
down_revision = "20260503_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "system_secrets",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("encrypted_value", sa.Text(), nullable=False),
        sa.Column("key_mask", sa.String(length=64), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("updated_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["updated_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", name="uq_system_secrets_name"),
    )
    op.create_index(op.f("ix_system_secrets_name"), "system_secrets", ["name"], unique=False)
    op.create_index(op.f("ix_system_secrets_updated_by_user_id"), "system_secrets", ["updated_by_user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_system_secrets_updated_by_user_id"), table_name="system_secrets")
    op.drop_index(op.f("ix_system_secrets_name"), table_name="system_secrets")
    op.drop_table("system_secrets")

