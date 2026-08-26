"""Track shared ingestion runs independent of user profiles."""

import sqlalchemy as sa

from alembic import op

revision = "0009_ingestion_runs"
down_revision = "0008_job_sources"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ingestion_runs",
        sa.Column("run_id", sa.String, primary_key=True),
        sa.Column("status", sa.String, nullable=False),
        sa.Column("trigger", sa.String, nullable=False),
        sa.Column("trigger_user_id", sa.String),
        sa.Column("source_filter", sa.JSON),
        sa.Column("result_json", sa.JSON),
        sa.Column("error", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("idx_ingestion_runs_status", "ingestion_runs", ["status"])
    op.create_index("idx_ingestion_runs_created", "ingestion_runs", ["created_at"])


def downgrade() -> None:
    op.drop_index("idx_ingestion_runs_created")
    op.drop_index("idx_ingestion_runs_status")
    op.drop_table("ingestion_runs")
