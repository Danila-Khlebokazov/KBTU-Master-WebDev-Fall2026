"""Initial and demo data. Runs on API startup; can also be run manually: `python -m app.seed`."""

import asyncio
import logging
import random
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import select

from app.db import SessionLocal, engine
from app.models import Category, Expense, Role, User
from app.security import hash_password
from app.settings import get_settings

settings = get_settings()
logger = logging.getLogger("uvicorn.error")

DEFAULT_CATEGORIES = [
    ("Food", "#f97316"),
    ("Transport", "#0ea5e9"),
    ("Housing", "#8b5cf6"),
    ("Entertainment", "#ec4899"),
    ("Health", "#22c55e"),
    ("Education", "#eab308"),
    ("Other", "#64748b"),
]

DEMO_USERS = [
    ("aruzhan@example.com", "Aruzhan Nurlanovna"),
    ("timur@example.com", "Timur Bekov"),
    ("dana@example.com", "Dana Sultanova"),
    ("alikhan@example.com", "Alikhan Zhumabayev"),
    ("madina@example.com", "Madina Akhmetova"),
]

# category -> [(title, min KZT, max KZT, relative frequency)]
EXPENSE_TEMPLATES: dict[str, list[tuple[str, int, int, int]]] = {
    "Food": [
        ("Groceries at Magnum", 6000, 25000, 6),
        ("Lunch at university canteen", 1500, 3500, 6),
        ("Coffee", 900, 2200, 6),
        ("Dinner with friends", 8000, 25000, 2),
        ("Pizza delivery (Wolt)", 5000, 12000, 2),
        ("Bakery", 600, 2500, 3),
        ("Fruits at Green Bazaar", 2000, 7000, 2),
    ],
    "Transport": [
        ("Taxi (Yandex Go)", 1200, 4500, 6),
        ("Bus card top-up (Onay)", 2000, 5000, 3),
        ("Fuel", 10000, 25000, 2),
        ("Car wash", 3000, 6000, 1),
        ("Parking", 500, 2000, 2),
        ("Train ticket Almaty - Astana", 12000, 30000, 1),
    ],
    "Housing": [
        ("Monthly rent", 150000, 250000, 1),
        ("Utilities", 12000, 30000, 1),
        ("Home internet", 6000, 9000, 1),
        ("Mobile plan", 3000, 6000, 1),
        ("Household supplies", 3000, 12000, 2),
    ],
    "Entertainment": [
        ("Cinema tickets", 3000, 7000, 3),
        ("Concert ticket", 15000, 45000, 1),
        ("Netflix subscription", 3500, 3500, 1),
        ("Spotify Premium", 1990, 1990, 1),
        ("Bowling night", 6000, 15000, 1),
        ("Board games cafe", 3000, 8000, 1),
        ("Steam game", 4000, 20000, 1),
    ],
    "Health": [
        ("Pharmacy", 1500, 9000, 3),
        ("Gym membership", 15000, 25000, 1),
        ("Dentist appointment", 10000, 40000, 1),
        ("Vitamins", 4000, 10000, 1),
        ("Doctor consultation", 8000, 15000, 1),
    ],
    "Education": [
        ("Udemy course", 5000, 12000, 1),
        ("Books", 3000, 12000, 2),
        ("Stationery", 1000, 5000, 2),
        ("English speaking club", 8000, 15000, 1),
        ("Conference ticket", 20000, 60000, 1),
    ],
    "Other": [
        ("Birthday gift", 8000, 30000, 1),
        ("Haircut", 4000, 10000, 2),
        ("Clothes", 10000, 45000, 2),
        ("Charity donation", 2000, 10000, 1),
        ("Phone repair", 10000, 35000, 1),
    ],
}
CATEGORY_WEIGHTS = {
    "Food": 40,
    "Transport": 20,
    "Housing": 8,
    "Entertainment": 12,
    "Health": 7,
    "Education": 7,
    "Other": 6,
}
NOTES = [
    "Paid with Kaspi Gold",
    "Split with a friend",
    "Cash",
    "Discount applied",
    "Monthly payment",
    "Was on sale",
]
HISTORY_DAYS = 180


async def seed_initial_data() -> None:
    """Admin account and default categories (idempotent)."""
    async with SessionLocal() as session:
        admin_email = settings.ADMIN_EMAIL.lower()
        if not await session.scalar(select(User.id).where(User.email == admin_email)):
            session.add(
                User(
                    email=admin_email,
                    full_name=settings.ADMIN_FULL_NAME,
                    hashed_password=hash_password(settings.ADMIN_PASSWORD),
                    role=Role.ADMIN,
                )
            )
            logger.info("Seeded admin user %s", admin_email)
        if not await session.scalar(select(Category.id).limit(1)):
            session.add_all(Category(name=n, color=c) for n, c in DEFAULT_CATEGORIES)
            logger.info("Seeded default categories")
        await session.commit()


def _random_expenses(rng: random.Random, owner: User, categories: dict[str, Category], count: int):
    today = date.today()
    names = list(CATEGORY_WEIGHTS)
    weights = list(CATEGORY_WEIGHTS.values())
    for _ in range(count):
        cat_name = rng.choices(names, weights)[0]
        templates = EXPENSE_TEMPLATES[cat_name]
        title, low, high, _w = rng.choices(templates, [t[3] for t in templates])[0]
        amount = Decimal(rng.randint(low, high)) if low != high else Decimal(low)
        yield Expense(
            title=title,
            amount=amount,
            # Triangular distribution: recent days are more likely, so the current month isn't empty
            spent_on=today - timedelta(days=int(rng.triangular(0, HISTORY_DAYS, 0))),
            note=rng.choice(NOTES) if rng.random() < 0.25 else None,
            category=categories.get(cat_name),
            owner=owner,
        )


async def seed_demo_data() -> int:
    """Demo users with ~6 months of expenses. Skipped if demo users already exist."""
    async with SessionLocal() as session:
        if await session.scalar(select(User.id).where(User.email == DEMO_USERS[0][0])):
            return 0

        categories = {c.name: c for c in await session.scalars(select(Category))}
        admin = await session.scalar(select(User).where(User.email == settings.ADMIN_EMAIL.lower()))
        rng = random.Random(42)
        password_hash = hash_password(settings.DEMO_USER_PASSWORD)

        expenses: list[Expense] = []
        for email, full_name in DEMO_USERS:
            user = User(email=email, full_name=full_name, hashed_password=password_hash)
            session.add(user)
            expenses.extend(_random_expenses(rng, user, categories, rng.randint(35, 50)))
        if admin is not None:
            expenses.extend(_random_expenses(rng, admin, categories, 25))

        session.add_all(expenses)
        await session.commit()
        logger.info("Seeded %d demo users and %d demo expenses", len(DEMO_USERS), len(expenses))
        return len(expenses)


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    await seed_initial_data()
    created = await seed_demo_data()
    await engine.dispose()
    print(f"Demo expenses created: {created}" if created else "Demo data already present")


if __name__ == "__main__":
    asyncio.run(main())
