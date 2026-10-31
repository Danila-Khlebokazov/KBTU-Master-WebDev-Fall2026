from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class HuntLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    criminal_id: int
    success: bool
    notes: str
    created_at: datetime


class HuntLogCreate(BaseModel):
    # extra="forbid" rejects client-supplied fields such as created_at
    model_config = ConfigDict(extra="forbid")

    criminal_id: int = Field(gt=0)
    success: bool
    notes: str = Field(min_length=1)


class HuntLogUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    success: bool | None = None
    notes: str | None = Field(default=None, min_length=1)


class CriminalOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str | None
    nickname: str
    reward: Decimal
    latitude: float | None
    longitude: float | None
    location_note: str | None
    difficulty: int
    armed: bool
    has_crew: bool
    escape_master: bool


class CriminalDetail(CriminalOut):
    hunts: list[HuntLogOut]
