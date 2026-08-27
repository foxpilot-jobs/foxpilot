"""Finalize canonical jobs and source-listing relationships."""

import hashlib
import json
import re

import sqlalchemy as sa

from alembic import op

revision = "0012_canonical_job_contract"
down_revision = "0011_pagination_indexes"
branch_labels = None
depends_on = None


def _normalise(value: object) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(value or "").lower()).strip()


def _content_hash(row: dict) -> str:
    content = {
        key: _normalise(row.get(key))
        for key in ("title", "company", "location", "description", "work_type")
    }
    return hashlib.sha256(
        json.dumps(content, sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()


def upgrade() -> None:
    op.add_column(
        "jobs",
        sa.Column(
            "canonical_content_hash", sa.String(), nullable=False, server_default=""
        ),
    )
    op.add_column(
        "jobs",
        sa.Column("normalized_company", sa.String(), nullable=False, server_default=""),
    )
    op.add_column(
        "jobs",
        sa.Column(
            "normalized_location", sa.String(), nullable=False, server_default=""
        ),
    )
    op.add_column(
        "jobs",
        sa.Column(
            "active_listing_count", sa.Integer(), nullable=False, server_default="0"
        ),
    )
    op.add_column(
        "job_listings",
        sa.Column("source_requisition_id", sa.String(), nullable=True),
    )
    op.add_column(
        "job_listings",
        sa.Column("source_url_history", sa.JSON(), nullable=False, server_default="[]"),
    )

    connection = op.get_bind()
    jobs = connection.execute(
        sa.text(
            "SELECT job_id, title, company, location, description, work_type FROM jobs"
        )
    ).mappings()
    for row in jobs:
        connection.execute(
            sa.text(
                "UPDATE jobs SET canonical_content_hash = :content_hash, "
                "normalized_company = :company, normalized_location = :location "
                "WHERE job_id = :job_id"
            ),
            {
                "content_hash": _content_hash(row),
                "company": _normalise(row["company"]),
                "location": _normalise(row["location"]),
                "job_id": row["job_id"],
            },
        )
    connection.execute(
        sa.text(
            "UPDATE job_listings SET source_requisition_id = source_job_id "
            "WHERE source_requisition_id IS NULL"
        )
    )
    connection.execute(
        sa.text(
            "UPDATE jobs SET active_listing_count = ("
            "SELECT COUNT(*) FROM job_listings "
            "WHERE job_listings.job_id = jobs.job_id "
            "AND job_listings.availability_status = 'active')"
        )
    )

    with op.batch_alter_table("job_listings", recreate="always") as batch:
        batch.alter_column("source_requisition_id", nullable=False)
        batch.create_foreign_key(
            "fk_job_listings_job_id", "jobs", ["job_id"], ["job_id"]
        )
        batch.create_foreign_key(
            "fk_job_listings_owner_user_id", "users", ["owner_user_id"], ["user_id"]
        )

    with op.batch_alter_table("matches", recreate="always") as batch:
        batch.create_foreign_key("fk_matches_job_id", "jobs", ["job_id"], ["job_id"])
        batch.create_foreign_key(
            "fk_matches_user_id", "users", ["user_id"], ["user_id"]
        )

    with op.batch_alter_table("applications", recreate="always") as batch:
        batch.create_foreign_key(
            "fk_applications_job_id", "jobs", ["job_id"], ["job_id"]
        )
        batch.create_foreign_key(
            "fk_applications_user_id", "users", ["user_id"], ["user_id"]
        )

    op.create_index("idx_jobs_content_hash", "jobs", ["canonical_content_hash"])
    op.create_index(
        "idx_job_listings_requisition",
        "job_listings",
        ["source", "source_requisition_id"],
    )


def downgrade() -> None:
    op.drop_index("idx_job_listings_requisition", table_name="job_listings")
    op.drop_index("idx_jobs_content_hash", table_name="jobs")

    with op.batch_alter_table("applications", recreate="always") as batch:
        batch.drop_constraint("fk_applications_user_id", type_="foreignkey")
        batch.drop_constraint("fk_applications_job_id", type_="foreignkey")
    with op.batch_alter_table("matches", recreate="always") as batch:
        batch.drop_constraint("fk_matches_user_id", type_="foreignkey")
        batch.drop_constraint("fk_matches_job_id", type_="foreignkey")
    with op.batch_alter_table("job_listings", recreate="always") as batch:
        batch.drop_constraint("fk_job_listings_owner_user_id", type_="foreignkey")
        batch.drop_constraint("fk_job_listings_job_id", type_="foreignkey")
        batch.drop_column("source_url_history")
        batch.drop_column("source_requisition_id")

    op.drop_column("jobs", "active_listing_count")
    op.drop_column("jobs", "normalized_location")
    op.drop_column("jobs", "normalized_company")
    op.drop_column("jobs", "canonical_content_hash")
