"""Track canonical jobs, source listings, and listing availability."""

import sqlalchemy as sa

from alembic import op

revision = "0008_job_sources"
down_revision = "0007_google_identity"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("jobs", sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()))
    op.add_column("jobs", sa.Column("last_seen_at", sa.DateTime(timezone=True)))
    op.add_column("jobs", sa.Column("inactive_at", sa.DateTime(timezone=True)))
    op.add_column("jobs", sa.Column("canonical_key", sa.String()))
    op.execute("UPDATE jobs SET last_seen_at = updated_at WHERE last_seen_at IS NULL")
    op.create_index("idx_jobs_active_updated", "jobs", ["is_active", "updated_at"])
    op.create_index("idx_jobs_canonical_key", "jobs", ["canonical_key"])

    op.create_table(
        "job_listings",
        sa.Column("listing_id", sa.String(), primary_key=True),
        sa.Column("listing_key", sa.String(), nullable=False),
        sa.Column("job_id", sa.String(), nullable=False),
        sa.Column("source", sa.String(), nullable=False),
        sa.Column("source_job_id", sa.String(), nullable=False),
        sa.Column("url", sa.String(), nullable=False, server_default=""),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.Column("availability_status", sa.String(), nullable=False, server_default="active"),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_checked_at", sa.DateTime(timezone=True)),
        sa.Column("unavailable_since", sa.DateTime(timezone=True)),
        sa.Column("check_failures", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status_reason", sa.String()),
        sa.Column("visibility", sa.String(), nullable=False, server_default="public"),
        sa.Column("owner_user_id", sa.String()),
        sa.UniqueConstraint("listing_key"),
    )
    op.execute(
        "INSERT INTO job_listings "
        "(listing_id, listing_key, job_id, source, source_job_id, url, payload_json, "
        "availability_status, first_seen_at, last_seen_at, last_checked_at, check_failures) "
        "SELECT job_id, 'public:' || source || ':' || source_job_id, job_id, source, source_job_id, url, payload_json, "
        "CASE WHEN is_active THEN 'active' ELSE 'inactive' END, created_at, "
        "COALESCE(last_seen_at, updated_at), updated_at, 0 FROM jobs"
    )
    op.create_index("idx_job_listings_job", "job_listings", ["job_id", "availability_status"])
    op.create_index("idx_job_listings_check", "job_listings", ["availability_status", "last_checked_at"])


def downgrade() -> None:
    op.drop_index("idx_job_listings_check", table_name="job_listings")
    op.drop_index("idx_job_listings_job", table_name="job_listings")
    op.drop_table("job_listings")
    op.drop_index("idx_jobs_canonical_key", table_name="jobs")
    op.drop_index("idx_jobs_active_updated", table_name="jobs")
    op.drop_column("jobs", "canonical_key")
    op.drop_column("jobs", "inactive_at")
    op.drop_column("jobs", "last_seen_at")
    op.drop_column("jobs", "is_active")
