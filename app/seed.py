from decimal import Decimal

from sqlalchemy import func, select

from app.db import SessionLocal
from app.models import HuntLog, WantedCriminal

CRIMINALS = [
    dict(name="Asimov Solensan", nickname="Red Eye Dealer", reward=Decimal("2500000"),
         latitude=12.5, longitude=45.2, location_note=None, difficulty=8,
         armed=True, has_crew=True, escape_master=False),
    dict(name=None, nickname="Teddy Bomber", reward=Decimal("1500000"),
         latitude=None, longitude=None, location_note="Last seen near the Tharsis gate on Mars",
         difficulty=6, armed=True, has_crew=False, escape_master=True),
    dict(name="Mad Pierrot", nickname="Pierrot le Fou", reward=Decimal("9000000"),
         latitude=-33.9, longitude=151.2, location_note=None, difficulty=10,
         armed=True, has_crew=False, escape_master=True),
    dict(name="Abdul Hakim", nickname="The Chameleon", reward=Decimal("3000"),
         latitude=None, longitude=None, location_note="Hiding in a Callisto bar",
         difficulty=4, armed=False, has_crew=False, escape_master=True),
    dict(name="Vincent Volaju", nickname="Ghost of Titan", reward=Decimal("30000000"),
         latitude=48.8, longitude=2.3, location_note=None, difficulty=9,
         armed=True, has_crew=True, escape_master=False),
    dict(name=None, nickname="Space Warrior", reward=Decimal("4500"),
         latitude=None, longitude=None, location_note="Drifting in the Ganymede asteroid belt",
         difficulty=2, armed=False, has_crew=True, escape_master=False),
]

HUNTS = [
    (1, False, "Target escaped through an asteroid field."),
    (1, False, "Ambushed by his crew at the Tijuana docks."),
    (2, False, "Bomb detonated, target vanished in the smoke."),
    (2, True, "Captured at the Tharsis gate after a long chase."),
    (3, False, "Bullets did not work, retreated with injuries."),
    (3, False, "Lost track in the amusement park."),
    (4, True, "Identified despite disguise, arrested quietly."),
    (5, False, "Train hijacked, target jumped off the bridge."),
    (5, False, "Nanomachine virus forced evacuation of the area."),
    (6, True, "Crew surrendered without a fight."),
    (6, False, "Ship engines failed, target got away."),
]


async def seed_data() -> None:
    async with SessionLocal() as session:
        if await session.scalar(select(func.count()).select_from(WantedCriminal)):
            return
        criminals = [WantedCriminal(**data) for data in CRIMINALS]
        session.add_all(criminals)
        await session.flush()
        session.add_all(
            HuntLog(criminal_id=criminals[idx - 1].id, success=success, notes=notes)
            for idx, success, notes in HUNTS
        )
        await session.commit()
