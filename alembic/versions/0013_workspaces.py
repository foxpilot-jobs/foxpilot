"""Add workspaces and migrate profiles to workspace-scoped rows."""

import sqlalchemy as sa

from alembic import op

revision = "0013_workspaces"
down_revision = "0012_canonical_job_contract"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "workspaces",
        sa.Column("workspace_id", sa.String(), primary_key=True),
        sa.Column(
            "user_id", sa.String(), sa.ForeignKey("users.user_id"), nullable=False
        ),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("idx_workspaces_user_id", "workspaces", ["user_id"])

    # Migrate existing profiles: create one default workspace per user, then add
    # workspace_id FK to profiles.
    op.add_column(
        "profiles",
        sa.Column("workspace_id", sa.String(), nullable=True),
    )

    connection = op.get_bind()

    # For every existing profile, create a "Default" workspace for that user and
    # link it.  The workspace owns the profile row.
    profiles = connection.execute(
        sa.text("SELECT user_id, created_at, updated_at FROM profiles")
    ).fetchall()
    for row in profiles:
        wid = f"ws_default_{row[0]}"
        connection.execute(
            sa.text(
                "INSERT INTO workspaces (workspace_id, user_id, name, is_active, "
                "created_at, updated_at) VALUES (:wid, :uid, :name, :active, :ca, :ua)"
            ),
            {
                "wid": wid,
                "uid": row[0],
                "name": "Default",
                "active": True,
                "ca": row[1],
                "ua": row[2],
            },
        )
        connection.execute(
            sa.text("UPDATE profiles SET workspace_id = :wid WHERE user_id = :uid"),
            {"wid": wid, "uid": row[0]},
        )

    # Enforce NOT NULL + FK + unique on workspace_id now that backfill is done.
    with op.batch_alter_table("profiles", recreate="always") as batch:
        batch.alter_column("workspace_id", nullable=False)
        batch.create_foreign_key(
            "fk_profiles_workspace_id", "workspaces", ["workspace_id"], ["workspace_id"]
        )
        batch.create_unique_constraint(
            "uq_profiles_user_workspace", ["user_id", "workspace_id"]
        )


def downgrade() -> None:
    with op.batch_alter_table("profiles", recreate="always") as batch:
        batch.drop_constraint("uq_profiles_user_workspace", type_="unique")
        batch.drop_constraint("fk_profiles_workspace_id", type_="foreignkey")
        batch.drop_column("workspace_id")

    op.drop_index("idx_workspaces_user_id", table_name="workspaces")
    op.drop_table("workspaces")
