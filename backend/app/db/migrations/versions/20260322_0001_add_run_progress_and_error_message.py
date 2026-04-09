"""Add run progress and error_message fields.

Revision ID: 20260322_0001
Revises:
Create Date: 2026-03-22 15:30:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "20260322_0001"
down_revision = None
branch_labels = None
depends_on = None


CORE_TABLES = (
    "users",
    "jobs",
    "runs",
    "results",
    "exports",
    "logs",
)


def _has_table(inspector: sa.Inspector, table_name: str) -> bool:
    return inspector.has_table(table_name)


def _get_column_names(inspector: sa.Inspector, table_name: str) -> set[str]:
    if not _has_table(inspector, table_name):
        return set()
    return {column["name"] for column in inspector.get_columns(table_name)}


def _create_baseline_schema(inspector: sa.Inspector) -> None:
    if not _has_table(inspector, "users"):
        op.create_table(
            "users",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text("gen_random_uuid()")),
            sa.Column("email", sa.String(length=255), nullable=False),
            sa.Column("hashed_password", sa.String(length=255), nullable=False),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
            sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
        )
        op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)

    if not _has_table(inspector, "jobs"):
        op.create_table(
            "jobs",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text("gen_random_uuid()")),
            sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("url", sa.Text(), nullable=False),
            sa.Column("login_url", sa.Text(), nullable=True),
            sa.Column("login_username", sa.String(length=255), nullable=True),
            sa.Column("login_password", sa.String(length=512), nullable=True),
            sa.Column("scrape_type", sa.String(length=50), nullable=False, server_default=sa.text("'general'")),
            sa.Column("config", postgresql.JSON(astext_type=sa.Text()), nullable=True),
            sa.Column("status", sa.String(length=20), nullable=False, server_default=sa.text("'pending'")),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE", name=op.f("fk_jobs_user_id_users")),
            sa.PrimaryKeyConstraint("id", name=op.f("pk_jobs")),
        )
        op.create_index(op.f("ix_jobs_status"), "jobs", ["status"], unique=False)
        op.create_index(op.f("ix_jobs_user_id"), "jobs", ["user_id"], unique=False)

    if not _has_table(inspector, "runs"):
        op.create_table(
            "runs",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text("gen_random_uuid()")),
            sa.Column("job_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("status", sa.String(length=20), nullable=False, server_default=sa.text("'pending'")),
            sa.Column("progress", sa.Integer(), nullable=False, server_default=sa.text("0")),
            sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("error", sa.Text(), nullable=True),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.Column("pages_scraped", sa.Integer(), nullable=False, server_default=sa.text("0")),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], ondelete="CASCADE", name=op.f("fk_runs_job_id_jobs")),
            sa.PrimaryKeyConstraint("id", name=op.f("pk_runs")),
        )
        op.create_index(op.f("ix_runs_job_id"), "runs", ["job_id"], unique=False)
        op.create_index(op.f("ix_runs_status"), "runs", ["status"], unique=False)

    if not _has_table(inspector, "results"):
        op.create_table(
            "results",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text("gen_random_uuid()")),
            sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("data_json", postgresql.JSON(astext_type=sa.Text()), nullable=False),
            sa.Column("data_type", sa.String(length=50), nullable=False),
            sa.Column("raw_html_path", sa.String(length=500), nullable=True),
            sa.Column("screenshot_path", sa.String(length=500), nullable=True),
            sa.Column("url", sa.Text(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.ForeignKeyConstraint(["run_id"], ["runs.id"], ondelete="CASCADE", name=op.f("fk_results_run_id_runs")),
            sa.PrimaryKeyConstraint("id", name=op.f("pk_results")),
        )
        op.create_index(op.f("ix_results_data_type"), "results", ["data_type"], unique=False)
        op.create_index(op.f("ix_results_run_id"), "results", ["run_id"], unique=False)

    if not _has_table(inspector, "exports"):
        op.create_table(
            "exports",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text("gen_random_uuid()")),
            sa.Column("result_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("format", sa.String(length=20), nullable=False),
            sa.Column("file_path", sa.String(length=500), nullable=False),
            sa.Column("file_size", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.ForeignKeyConstraint(["result_id"], ["results.id"], ondelete="SET NULL", name=op.f("fk_exports_result_id_results")),
            sa.ForeignKeyConstraint(["run_id"], ["runs.id"], ondelete="SET NULL", name=op.f("fk_exports_run_id_runs")),
            sa.PrimaryKeyConstraint("id", name=op.f("pk_exports")),
        )
        op.create_index(op.f("ix_exports_format"), "exports", ["format"], unique=False)
        op.create_index(op.f("ix_exports_result_id"), "exports", ["result_id"], unique=False)
        op.create_index(op.f("ix_exports_run_id"), "exports", ["run_id"], unique=False)

    if not _has_table(inspector, "logs"):
        op.create_table(
            "logs",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text("gen_random_uuid()")),
            sa.Column("agent_name", sa.String(length=100), nullable=False),
            sa.Column("action", sa.String(length=100), nullable=False),
            sa.Column("input_data", postgresql.JSON(astext_type=sa.Text()), nullable=True),
            sa.Column("output_data", postgresql.JSON(astext_type=sa.Text()), nullable=True),
            sa.Column("error", sa.Text(), nullable=True),
            sa.Column("status", sa.String(length=20), nullable=False, server_default=sa.text("'success'")),
            sa.Column("execution_time", sa.Float(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.PrimaryKeyConstraint("id", name=op.f("pk_logs")),
        )
        op.create_index(op.f("ix_logs_agent_name"), "logs", ["agent_name"], unique=False)
        op.create_index(op.f("ix_logs_created_at"), "logs", ["created_at"], unique=False)
        op.create_index(op.f("ix_logs_status"), "logs", ["status"], unique=False)


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not any(_has_table(inspector, table_name) for table_name in CORE_TABLES):
        _create_baseline_schema(inspector)
        return

    run_columns = _get_column_names(inspector, "runs")
    if "progress" not in run_columns:
        op.add_column("runs", sa.Column("progress", sa.Integer(), nullable=False, server_default=sa.text("0")))
        op.execute(sa.text("UPDATE runs SET progress = 0 WHERE progress IS NULL"))
        op.alter_column("runs", "progress", server_default=None)

    if "error_message" not in run_columns:
        op.add_column("runs", sa.Column("error_message", sa.Text(), nullable=True))
        op.execute(sa.text("UPDATE runs SET error_message = error WHERE error_message IS NULL AND error IS NOT NULL"))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if all(_has_table(inspector, table_name) for table_name in CORE_TABLES):
        op.drop_index(op.f("ix_logs_status"), table_name="logs")
        op.drop_index(op.f("ix_logs_created_at"), table_name="logs")
        op.drop_index(op.f("ix_logs_agent_name"), table_name="logs")
        op.drop_table("logs")

        op.drop_index(op.f("ix_exports_run_id"), table_name="exports")
        op.drop_index(op.f("ix_exports_result_id"), table_name="exports")
        op.drop_index(op.f("ix_exports_format"), table_name="exports")
        op.drop_table("exports")

        op.drop_index(op.f("ix_results_run_id"), table_name="results")
        op.drop_index(op.f("ix_results_data_type"), table_name="results")
        op.drop_table("results")

        op.drop_index(op.f("ix_runs_status"), table_name="runs")
        op.drop_index(op.f("ix_runs_job_id"), table_name="runs")
        op.drop_table("runs")

        op.drop_index(op.f("ix_jobs_user_id"), table_name="jobs")
        op.drop_index(op.f("ix_jobs_status"), table_name="jobs")
        op.drop_table("jobs")

        op.drop_index(op.f("ix_users_email"), table_name="users")
        op.drop_table("users")
        return

    run_columns = _get_column_names(inspector, "runs")
    if "error_message" in run_columns:
        op.drop_column("runs", "error_message")
    if "progress" in run_columns:
        op.drop_column("runs", "progress")
