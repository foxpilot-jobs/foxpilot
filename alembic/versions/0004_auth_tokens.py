"""Add one-time email verification and password reset tokens."""

import sqlalchemy as sa

from alembic import op

revision = "0004_auth_tokens"
down_revision = "0003_native_auth"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "auth_tokens",
        sa.Column("token_id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("purpose", sa.String(), nullable=False),
        sa.Column("token_hash", sa.String(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_index("idx_auth_tokens_lookup", "auth_tokens", ["token_hash", "purpose"])


def downgrade() -> None:
    op.drop_index("idx_auth_tokens_lookup", table_name="auth_tokens")
    op.drop_table("auth_tokens")
