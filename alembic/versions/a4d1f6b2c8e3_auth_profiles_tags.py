"""auth columns, profiles (1:1) and tags (M:N with tasks)

Revision ID: a4d1f6b2c8e3
Revises: 7c1e5d8f2a90
Create Date: 2026-11-24 12:00:00.000000

"""

from collections.abc import Sequence

import bcrypt
import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a4d1f6b2c8e3"
down_revision: str | Sequence[str] | None = "7c1e5d8f2a90"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

DEMO_DOMAIN = "demo.example.com"
DEMO_PASSWORD = "password123"
# Not a valid bcrypt hash -> nobody can log in until the password is reset
UNUSABLE_PASSWORD = "!"


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("users", sa.Column("username", sa.String(length=50), nullable=True))
    op.add_column(
        "users", sa.Column("hashed_password", sa.String(length=255), nullable=True)
    )
    op.add_column(
        "users",
        sa.Column("token_version", sa.Integer(), server_default="0", nullable=False),
    )

    # Backfill existing users: demo users get "<local part>" + a known password,
    # any other pre-existing users get "<local part>_<id>" and an unusable password.
    conn = op.get_bind()
    rows = conn.execute(sa.text("SELECT id, email FROM users")).all()
    for user_id, email in rows:
        local = email.split("@", 1)[0].lower()
        if email.endswith(f"@{DEMO_DOMAIN}"):
            username = local[:50]
            password = bcrypt.hashpw(DEMO_PASSWORD.encode(), bcrypt.gensalt()).decode()
        else:
            username = f"{local[:40]}_{user_id}"
            password = UNUSABLE_PASSWORD
        conn.execute(
            sa.text(
                "UPDATE users SET username = :u, hashed_password = :p WHERE id = :id"
            ),
            {"u": username, "p": password, "id": user_id},
        )

    op.alter_column("users", "username", nullable=False)
    op.alter_column("users", "hashed_password", nullable=False)
    op.create_index(op.f("ix_users_username"), "users", ["username"], unique=True)

    op.create_table(
        "profiles",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("bio", sa.Text(), nullable=True),
        sa.Column("job_title", sa.String(length=100), nullable=True),
        sa.Column("location", sa.String(length=100), nullable=True),
        sa.Column("website", sa.String(length=255), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id"),
    )

    op.create_table(
        "tags",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=50), nullable=False),
        sa.Column("color", sa.String(length=7), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )

    op.create_table(
        "task_tags",
        sa.Column("task_id", sa.Integer(), nullable=False),
        sa.Column("tag_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tag_id"], ["tags.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("task_id", "tag_id"),
    )
    op.create_index(op.f("ix_task_tags_tag_id"), "task_tags", ["tag_id"])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_task_tags_tag_id"), table_name="task_tags")
    op.drop_table("task_tags")
    op.drop_table("tags")
    op.drop_table("profiles")
    op.drop_index(op.f("ix_users_username"), table_name="users")
    op.drop_column("users", "token_version")
    op.drop_column("users", "hashed_password")
    op.drop_column("users", "username")
