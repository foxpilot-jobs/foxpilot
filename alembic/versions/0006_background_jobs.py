"""Add persisted background jobs for long-running local model work."""

import sqlalchemy as sa

from alembic import op

revision = "0006_background_jobs"
down_revision = "0005_user_profiles"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "background_jobs",
        sa.Column("job_id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("kind", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("result_json", sa.JSON()),
        sa.Column("error", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("idx_background_jobs_user", "background_jobs", ["user_id", "updated_at"])


def downgrade() -> None:
    op.drop_index("idx_background_jobs_user", table_name="background_jobs")
    op.drop_table("background_jobs")
