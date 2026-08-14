"""Add native password and session authentication fields."""

import sqlalchemy as sa

from alembic import op

revision = "0003_native_auth"
down_revision = "0002_user_owned_state"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("password_hash", sa.String()))
    op.add_column("users", sa.Column("email_verified", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("users", sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()))
    op.alter_column("users", "email_verified", server_default=None)
    op.alter_column("users", "is_active", server_default=None)
    op.create_index("idx_users_email", "users", ["email"], unique=True)
    op.create_table(
        "sessions",
        sa.Column("session_id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("token_hash", sa.String(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_index("idx_sessions_token_hash", "sessions", ["token_hash"])
    op.create_index("idx_sessions_user_id", "sessions", ["user_id"])


def downgrade() -> None:
    op.drop_index("idx_sessions_user_id", table_name="sessions")
    op.drop_index("idx_sessions_token_hash", table_name="sessions")
    op.drop_table("sessions")
    op.drop_index("idx_users_email", table_name="users")
    op.drop_column("users", "is_active")
    op.drop_column("users", "email_verified")
    op.drop_column("users", "password_hash")
