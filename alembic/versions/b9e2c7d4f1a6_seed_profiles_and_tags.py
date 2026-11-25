"""seed demo profiles, tags and task tags

Revision ID: b9e2c7d4f1a6
Revises: a4d1f6b2c8e3
Create Date: 2026-11-24 12:30:00.000000

"""

import random
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b9e2c7d4f1a6"
down_revision: str | Sequence[str] | None = "a4d1f6b2c8e3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

DEMO_DOMAIN = "demo.example.com"

PROFILES = [
    ("Product manager who loves clean roadmaps.", "Product Manager", "Almaty"),
    ("Backend developer, Python and PostgreSQL.", "Backend Engineer", "Astana"),
    ("Designing friendly interfaces since 2018.", "UI/UX Designer", "Almaty"),
    ("Keeps the CI green and the servers alive.", "DevOps Engineer", "Shymkent"),
    ("Frontend developer, React enthusiast.", "Frontend Engineer", "Almaty"),
    ("Breaks things so users don't have to.", "QA Engineer", "Karaganda"),
    ("Turning data into decisions.", "Data Analyst", "Astana"),
    ("Mobile apps for iOS and Android.", "Mobile Developer", "Aktobe"),
    ("Writes docs people actually read.", "Technical Writer", "Seoul"),
    ("Security first, features second.", "Security Engineer", "Almaty"),
    ("Helping the team ship on time.", "Scrum Master", "Pavlodar"),
    ("Full-stack generalist and coffee lover.", "Full-stack Engineer", "Kostanay"),
]

TAGS = [
    ("bug", "#ef4444"),
    ("feature", "#22c55e"),
    ("backend", "#3b82f6"),
    ("frontend", "#a855f7"),
    ("devops", "#f97316"),
    ("design", "#ec4899"),
    ("docs", "#64748b"),
    ("security", "#b91c1c"),
    ("performance", "#eab308"),
    ("testing", "#14b8a6"),
    ("urgent", "#dc2626"),
    ("research", "#0ea5e9"),
]


def upgrade() -> None:
    conn = op.get_bind()
    rng = random.Random(7)

    demo_users = conn.execute(
        sa.text("SELECT id, username FROM users WHERE email LIKE :d ORDER BY id"),
        {"d": f"%@{DEMO_DOMAIN}"},
    ).all()

    profiles = sa.table(
        "profiles",
        sa.column("user_id", sa.Integer),
        sa.column("bio"),
        sa.column("job_title"),
        sa.column("location"),
        sa.column("website"),
    )
    op.bulk_insert(
        profiles,
        [
            {
                "user_id": user_id,
                "bio": bio,
                "job_title": title,
                "location": location,
                "website": f"https://{username.replace('.', '-')}.dev",
            }
            for (user_id, username), (bio, title, location) in zip(
                demo_users, PROFILES, strict=False
            )
        ],
    )

    tags = sa.table(
        "tags", sa.column("id", sa.Integer), sa.column("name"), sa.column("color")
    )
    tag_ids = (
        conn.execute(
            tags.insert().returning(tags.c.id),
            [{"name": name, "color": color} for name, color in TAGS],
        )
        .scalars()
        .all()
    )

    demo_task_ids = (
        conn.execute(
            sa.text(
                "SELECT t.id FROM tasks t JOIN projects p ON p.id = t.project_id "
                "JOIN users u ON u.id = p.owner_id WHERE u.email LIKE :d ORDER BY t.id"
            ),
            {"d": f"%@{DEMO_DOMAIN}"},
        )
        .scalars()
        .all()
    )
    task_tags = sa.table(
        "task_tags", sa.column("task_id", sa.Integer), sa.column("tag_id", sa.Integer)
    )
    links = [
        {"task_id": task_id, "tag_id": tag_id}
        for task_id in demo_task_ids
        for tag_id in rng.sample(tag_ids, rng.randint(1, 3))
    ]
    if links:
        op.bulk_insert(task_tags, links)


def downgrade() -> None:
    """Remove seeded tags (links cascade) and demo profiles."""
    conn = op.get_bind()
    conn.execute(
        sa.text("DELETE FROM tags WHERE name = ANY(:names)"),
        {"names": [name for name, _ in TAGS]},
    )
    conn.execute(
        sa.text(
            "DELETE FROM profiles WHERE user_id IN "
            "(SELECT id FROM users WHERE email LIKE :d)"
        ),
        {"d": f"%@{DEMO_DOMAIN}"},
    )
