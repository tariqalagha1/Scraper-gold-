"""Encrypt persisted job login credentials.

Revision ID: 20260329_0004
Revises: 20260323_0003
Create Date: 2026-03-29 12:30:00
"""

from alembic import op
import sqlalchemy as sa

from app.core.secrets import decrypt_secret, encrypt_secret, is_encrypted_secret


revision = "20260329_0004"
down_revision = "20260323_0003"
branch_labels = None
depends_on = None


def _maybe_encrypt(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = str(value).strip()
    if not cleaned or is_encrypted_secret(cleaned):
        return cleaned
    return encrypt_secret(cleaned)


def upgrade() -> None:
    op.alter_column("jobs", "login_username", existing_type=sa.String(length=255), type_=sa.Text(), existing_nullable=True)
    op.alter_column("jobs", "login_password", existing_type=sa.String(length=512), type_=sa.Text(), existing_nullable=True)

    connection = op.get_bind()
    jobs = connection.execute(sa.text("SELECT id, login_username, login_password FROM jobs")).mappings().all()
    for job in jobs:
        encrypted_username = _maybe_encrypt(job["login_username"])
        encrypted_password = _maybe_encrypt(job["login_password"])
        if encrypted_username == job["login_username"] and encrypted_password == job["login_password"]:
            continue
        connection.execute(
            sa.text(
                """
                UPDATE jobs
                SET login_username = :login_username,
                    login_password = :login_password
                WHERE id = :job_id
                """
            ),
            {
                "job_id": job["id"],
                "login_username": encrypted_username,
                "login_password": encrypted_password,
            },
        )


def downgrade() -> None:
    connection = op.get_bind()
    jobs = connection.execute(sa.text("SELECT id, login_username, login_password FROM jobs")).mappings().all()
    for job in jobs:
        login_username = job["login_username"]
        login_password = job["login_password"]
        if login_username:
            try:
                login_username = decrypt_secret(login_username, allow_plaintext_fallback=True)
            except Exception:
                login_username = job["login_username"]
        if login_password:
            try:
                login_password = decrypt_secret(login_password, allow_plaintext_fallback=True)
            except Exception:
                login_password = job["login_password"]
        connection.execute(
            sa.text(
                """
                UPDATE jobs
                SET login_username = :login_username,
                    login_password = :login_password
                WHERE id = :job_id
                """
            ),
            {
                "job_id": job["id"],
                "login_username": login_username,
                "login_password": login_password,
            },
        )

    op.alter_column("jobs", "login_password", existing_type=sa.Text(), type_=sa.String(length=512), existing_nullable=True)
    op.alter_column("jobs", "login_username", existing_type=sa.Text(), type_=sa.String(length=255), existing_nullable=True)
