"""Add worker lease, retry, and progress columns to background_jobs."""

import sqlalchemy as sa

from alembic import op

revision = "0010_worker_contract"
down_revision = "0009_ingestion_runs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "background_jobs",
        sa.Column("attempt", sa.Integer, nullable=False, server_default="0"),
    )
    op.add_column(
        "background_jobs",
        sa.Column("max_attempts", sa.Integer, nullable=False, server_default="3"),
    )
    op.add_column("background_jobs", sa.Column("lease_owner", sa.String))
    op.add_column(
        "background_jobs", sa.Column("lease_expires_at", sa.DateTime(timezone=True))
    )
    op.add_column("background_jobs", sa.Column("error_class", sa.String))
    op.add_column(
        "background_jobs", sa.Column("started_at", sa.DateTime(timezone=True))
    )
    op.add_column("background_jobs", sa.Column("idempotency_key", sa.String))
    op.add_column("background_jobs", sa.Column("progress_json", sa.JSON))
    op.create_index(
        "idx_background_jobs_idempotency",
        "background_jobs",
        ["idempotency_key"],
        unique=True,
    )
    op.create_index(
        "idx_background_jobs_status_lease",
        "background_jobs",
        ["status", "lease_expires_at"],
    )


def downgrade() -> None:
    op.drop_index("idx_background_jobs_status_lease")
    op.drop_index("idx_background_jobs_idempotency")
    op.drop_column("background_jobs", "progress_json")
    op.drop_column("background_jobs", "idempotency_key")
    op.drop_column("background_jobs", "started_at")
    op.drop_column("background_jobs", "error_class")
    op.drop_column("background_jobs", "lease_expires_at")
    op.drop_column("background_jobs", "lease_owner")
    op.drop_column("background_jobs", "max_attempts")
    op.drop_column("background_jobs", "attempt")
