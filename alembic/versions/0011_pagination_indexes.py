"""Add indexes to support paginated, filtered, and sorted list queries."""

from alembic import op

revision = "0011_pagination_indexes"
down_revision = "0010_worker_contract"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index("idx_jobs_company", "jobs", ["company"])
    op.create_index("idx_jobs_location", "jobs", ["location"])
    op.create_index("idx_jobs_work_type", "jobs", ["work_type"])
    op.create_index("idx_jobs_source", "jobs", ["source"])
    op.create_index(
        "idx_job_listings_source_status",
        "job_listings",
        ["source", "availability_status"],
    )
    op.create_index(
        "idx_matches_user_updated",
        "matches",
        ["user_id", "updated_at"],
    )
    op.create_index(
        "idx_applications_user_status",
        "applications",
        ["user_id", "status", "updated_at"],
    )


def downgrade() -> None:
    op.drop_index("idx_applications_user_status")
    op.drop_index("idx_matches_user_updated")
    op.drop_index("idx_job_listings_source_status")
    op.drop_index("idx_jobs_source")
    op.drop_index("idx_jobs_work_type")
    op.drop_index("idx_jobs_location")
    op.drop_index("idx_jobs_company")
