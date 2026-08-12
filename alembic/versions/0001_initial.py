"""Initial FoxPilot storage schema."""

import sqlalchemy as sa

from alembic import op

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "jobs",
        sa.Column("job_id", sa.String(), primary_key=True),
        sa.Column("source", sa.String(), nullable=False),
        sa.Column("source_job_id", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("company", sa.String(), nullable=False),
        sa.Column("location", sa.String(), nullable=False),
        sa.Column("url", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("first_published", sa.String()),
        sa.Column("work_type", sa.String()),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.Column("local_relevance", sa.String()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("source", "source_job_id"),
    )
    op.create_index("idx_jobs_relevance", "jobs", ["local_relevance"])
    op.create_index("idx_jobs_updated", "jobs", ["updated_at"])
    op.create_table(
        "matches",
        sa.Column("job_id", sa.String(), primary_key=True),
        sa.Column("job_hash", sa.String(), nullable=False),
        sa.Column("provider", sa.String(), nullable=False),
        sa.Column("model", sa.String(), nullable=False),
        sa.Column("result_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "applications",
        sa.Column("job_id", sa.String(), primary_key=True),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=False),
        sa.Column("applied_at", sa.DateTime(timezone=True)),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("applications")
    op.drop_table("matches")
    op.drop_index("idx_jobs_updated", table_name="jobs")
    op.drop_index("idx_jobs_relevance", table_name="jobs")
    op.drop_table("jobs")
