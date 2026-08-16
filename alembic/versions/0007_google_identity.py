"""Add Google identity linking fields to users."""

import sqlalchemy as sa

from alembic import op

revision = "0007_google_identity"
down_revision = "0006_background_jobs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("auth_provider", sa.String()))
    op.add_column("users", sa.Column("auth_subject", sa.String()))
    op.create_index(
        "idx_users_auth_identity",
        "users",
        ["auth_provider", "auth_subject"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("idx_users_auth_identity", table_name="users")
    op.drop_column("users", "auth_subject")
    op.drop_column("users", "auth_provider")
