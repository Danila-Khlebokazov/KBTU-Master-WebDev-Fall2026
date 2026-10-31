from decimal import Decimal
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db import get_session
from app.models import WantedCriminal
from app.schemas import CriminalDetail, CriminalOut

router = APIRouter(prefix="/criminals", tags=["Criminals"])


@router.get("/", response_model=list[CriminalOut])
async def list_criminals(
    min_reward: Decimal | None = Query(None, ge=0),
    max_reward: Decimal | None = Query(None, ge=0),
    armed: bool | None = None,
    has_crew: bool | None = None,
    escape_master: bool | None = None,
    sort: Literal["reward", "-reward"] | None = None,
    session: AsyncSession = Depends(get_session),
):
    if min_reward is not None and max_reward is not None and min_reward > max_reward:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "min_reward must be less than or equal to max_reward"
        )

    stmt = select(WantedCriminal)
    if min_reward is not None:
        stmt = stmt.where(WantedCriminal.reward >= min_reward)
    if max_reward is not None:
        stmt = stmt.where(WantedCriminal.reward <= max_reward)
    if armed is not None:
        stmt = stmt.where(WantedCriminal.armed == armed)
    if has_crew is not None:
        stmt = stmt.where(WantedCriminal.has_crew == has_crew)
    if escape_master is not None:
        stmt = stmt.where(WantedCriminal.escape_master == escape_master)

    if sort == "reward":
        stmt = stmt.order_by(WantedCriminal.reward.asc(), WantedCriminal.id)
    elif sort == "-reward":
        stmt = stmt.order_by(WantedCriminal.reward.desc(), WantedCriminal.id)
    else:
        stmt = stmt.order_by(WantedCriminal.id)

    return (await session.scalars(stmt)).all()


@router.get("/{criminal_id}/", response_model=CriminalDetail)
async def get_criminal(criminal_id: int, session: AsyncSession = Depends(get_session)):
    criminal = await session.get(
        WantedCriminal, criminal_id, options=[selectinload(WantedCriminal.hunts)]
    )
    if criminal is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Criminal not found")
    return criminal
