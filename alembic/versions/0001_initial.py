"""initial schema: wanted_criminals, hunt_logs

Revision ID: 0001_initial
Revises:
Create Date: 2026-10-31

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "wanted_criminals",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(200), nullable=True),
        sa.Column("nickname", sa.String(200), nullable=False),
        sa.Column("reward", sa.Numeric(14, 2), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column("location_note", sa.Text(), nullable=True),
        sa.Column("difficulty", sa.Integer(), nullable=False),
        sa.Column("armed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("has_crew", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("escape_master", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.CheckConstraint("reward >= 0", name="ck_criminals_reward_non_negative"),
        sa.CheckConstraint("difficulty BETWEEN 1 AND 10", name="ck_criminals_difficulty_range"),
        sa.CheckConstraint("latitude BETWEEN -90 AND 90", name="ck_criminals_latitude_range"),
        sa.CheckConstraint("longitude BETWEEN -180 AND 180", name="ck_criminals_longitude_range"),
    )
    op.create_index("ix_wanted_criminals_reward", "wanted_criminals", ["reward"])

    op.create_table(
        "hunt_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "criminal_id",
            sa.Integer(),
            sa.ForeignKey("wanted_criminals.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("success", sa.Boolean(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index("ix_hunt_logs_criminal_id", "hunt_logs", ["criminal_id"])


def downgrade() -> None:
    op.drop_index("ix_hunt_logs_criminal_id", table_name="hunt_logs")
    op.drop_table("hunt_logs")
    op.drop_index("ix_wanted_criminals_reward", table_name="wanted_criminals")
    op.drop_table("wanted_criminals")
