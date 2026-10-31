from datetime import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class WantedCriminal(Base):
    __tablename__ = "wanted_criminals"
    __table_args__ = (
        CheckConstraint("reward >= 0", name="ck_criminals_reward_non_negative"),
        CheckConstraint("difficulty BETWEEN 1 AND 10", name="ck_criminals_difficulty_range"),
        CheckConstraint("latitude BETWEEN -90 AND 90", name="ck_criminals_latitude_range"),
        CheckConstraint("longitude BETWEEN -180 AND 180", name="ck_criminals_longitude_range"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str | None] = mapped_column(String(200))
    nickname: Mapped[str] = mapped_column(String(200))
    reward: Mapped[Decimal] = mapped_column(Numeric(14, 2), index=True)
    latitude: Mapped[float | None]
    longitude: Mapped[float | None]
    location_note: Mapped[str | None] = mapped_column(Text)
    difficulty: Mapped[int]
    armed: Mapped[bool] = mapped_column(default=False)
    has_crew: Mapped[bool] = mapped_column(default=False)
    escape_master: Mapped[bool] = mapped_column(default=False)

    hunts: Mapped[list["HuntLog"]] = relationship(
        back_populates="criminal", cascade="all, delete-orphan", passive_deletes=True
    )


class HuntLog(Base):
    __tablename__ = "hunt_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    criminal_id: Mapped[int] = mapped_column(
        ForeignKey("wanted_criminals.id", ondelete="CASCADE"), index=True
    )
    success: Mapped[bool]
    notes: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    criminal: Mapped[WantedCriminal] = relationship(back_populates="hunts")
