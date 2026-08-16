"""Store one private resume profile per user."""

import sqlalchemy as sa

from alembic import op

revision = "0005_user_profiles"
down_revision = "0004_auth_tokens"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "profiles",
        sa.Column("user_id", sa.String(), primary_key=True),
        sa.Column("resume_text", sa.Text(), nullable=False),
        sa.Column("resume_filename", sa.String(), nullable=False),
        sa.Column("profile_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("profiles")
