"""seed demo data

Revision ID: 7c1e5d8f2a90
Revises: 3b7f2c9a1d4e
Create Date: 2026-11-09 16:00:00.000000

"""

import random
from collections.abc import Sequence
from datetime import date, timedelta

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "7c1e5d8f2a90"
down_revision: str | Sequence[str] | None = "3b7f2c9a1d4e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

DEMO_DOMAIN = "demo.example.com"

USERS = [
    ("aruzhan.sadykova", "Aruzhan Sadykova"),
    ("daniyar.nurlanov", "Daniyar Nurlanov"),
    ("alina.kim", "Alina Kim"),
    ("timur.akhmetov", "Timur Akhmetov"),
    ("madina.zhaksylyk", "Madina Zhaksylyk"),
    ("ivan.petrov", "Ivan Petrov"),
    ("dana.omarova", "Dana Omarova"),
    ("yerlan.bekov", "Yerlan Bekov"),
    ("sofia.lee", "Sofia Lee"),
    ("arman.seitkali", "Arman Seitkali"),
    ("kamila.ospanova", "Kamila Ospanova"),
    ("nursultan.abenov", "Nursultan Abenov"),
]

PROJECTS = [
    ("Website redesign", "New marketing site and landing pages"),
    ("Mobile app v2", "iOS and Android release with offline mode"),
    ("Payments integration", "Kaspi and card payments"),
    ("Internal CRM", "Customer management tool for sales"),
    ("Data warehouse", "ETL pipelines and BI dashboards"),
    ("Onboarding flow", "Improve new user activation"),
    ("Security audit", "OWASP review and pentest fixes"),
    ("Recommendation engine", "Personalized product suggestions"),
    ("Support chatbot", "FAQ bot for customer support"),
    ("Infrastructure migration", "Move services to Kubernetes"),
    ("Analytics events", "Unified event tracking"),
    ("Admin panel", "Back-office for moderators"),
    ("Notifications service", "Email, push and SMS delivery"),
    ("Search improvements", "Full-text search and filters"),
    ("Accessibility pass", "WCAG 2.1 AA compliance"),
]

TASK_VERBS = [
    "Implement",
    "Design",
    "Review",
    "Test",
    "Refactor",
    "Document",
    "Fix",
    "Deploy",
]
TASK_OBJECTS = [
    "login page",
    "REST endpoints",
    "database schema",
    "CI pipeline",
    "error handling",
    "unit tests",
    "API docs",
    "caching layer",
    "user settings",
    "search filters",
    "email templates",
    "rate limiting",
    "logging",
    "dashboard charts",
    "file uploads",
]
STATUSES = ["todo", "in_progress", "done"]
TASKS_PER_PROJECT = 10


def upgrade() -> None:
    """Insert demo users, projects and 150 tasks."""
    conn = op.get_bind()
    rng = random.Random(42)

    users = sa.table(
        "users", sa.column("id", sa.Integer), sa.column("email"), sa.column("name")
    )
    projects = sa.table(
        "projects",
        sa.column("id", sa.Integer),
        sa.column("name"),
        sa.column("description"),
        sa.column("owner_id", sa.Integer),
    )
    tasks = sa.table(
        "tasks",
        sa.column("title"),
        sa.column("description"),
        sa.column("status"),
        sa.column("priority", sa.Integer),
        sa.column("due_date", sa.Date),
        sa.column("project_id", sa.Integer),
        sa.column("assignee_id", sa.Integer),
    )

    user_ids = (
        conn.execute(
            users.insert().returning(users.c.id),
            [
                {"email": f"{login}@{DEMO_DOMAIN}", "name": name}
                for login, name in USERS
            ],
        )
        .scalars()
        .all()
    )

    project_ids = (
        conn.execute(
            projects.insert().returning(projects.c.id),
            [
                {
                    "name": name,
                    "description": desc,
                    "owner_id": user_ids[i % len(user_ids)],
                }
                for i, (name, desc) in enumerate(PROJECTS)
            ],
        )
        .scalars()
        .all()
    )

    start = date(2026, 11, 1)
    task_rows = []
    for project_id in project_ids:
        for n in range(TASKS_PER_PROJECT):
            title = f"{rng.choice(TASK_VERBS)} {rng.choice(TASK_OBJECTS)}"
            task_rows.append(
                {
                    "title": title,
                    "description": f"Task #{n + 1}: {title.lower()}",
                    "status": rng.choice(STATUSES),
                    "priority": rng.randint(1, 5),
                    "due_date": start + timedelta(days=rng.randint(0, 90))
                    if rng.random() < 0.8
                    else None,
                    "project_id": project_id,
                    "assignee_id": rng.choice(user_ids)
                    if rng.random() < 0.85
                    else None,
                }
            )
    op.bulk_insert(tasks, task_rows)


def downgrade() -> None:
    """Remove demo data (projects and tasks are removed by FK cascade)."""
    op.execute(sa.text(f"DELETE FROM users WHERE email LIKE '%@{DEMO_DOMAIN}'"))
