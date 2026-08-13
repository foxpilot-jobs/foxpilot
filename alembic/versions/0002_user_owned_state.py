"""Add users and isolate matches and applications by user."""

import sqlalchemy as sa

from alembic import op

revision = "0002_user_owned_state"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("user_id", sa.String(), primary_key=True),
        sa.Column("email", sa.String()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.execute(
        "INSERT INTO users (user_id, email, created_at, updated_at) "
        "VALUES ('local-user', 'local@foxpilot.local', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
    )

    for table in ("matches", "applications"):
        op.add_column(
            table,
            sa.Column("user_id", sa.String(), nullable=False, server_default="local-user"),
        )
        op.drop_constraint(f"{table}_pkey", table_name=table, type_="primary")
        op.create_primary_key(f"{table}_pkey", table, ["user_id", "job_id"])
        op.alter_column(table, "user_id", server_default=None)
        op.create_index(f"idx_{table}_user", table, ["user_id"])


def downgrade() -> None:
    for table in ("applications", "matches"):
        op.drop_index(f"idx_{table}_user", table_name=table)
        op.drop_constraint(f"{table}_pkey", table_name=table, type_="primary")
        op.create_primary_key(f"{table}_pkey", table, ["job_id"])
        op.drop_column(table, "user_id")
    op.drop_table("users")
