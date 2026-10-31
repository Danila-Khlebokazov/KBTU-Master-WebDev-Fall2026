from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models import HuntLog, WantedCriminal
from app.schemas import HuntLogCreate, HuntLogOut, HuntLogUpdate

router = APIRouter(prefix="/hunts", tags=["Hunt logs"])


async def _get_hunt_or_404(session: AsyncSession, hunt_id: int) -> HuntLog:
    hunt = await session.get(HuntLog, hunt_id)
    if hunt is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Hunt log not found")
    return hunt


@router.get("/", response_model=list[HuntLogOut])
async def list_hunts(
    criminal_id: int | None = Query(None, gt=0),
    session: AsyncSession = Depends(get_session),
):
    stmt = select(HuntLog).order_by(HuntLog.id)
    if criminal_id is not None:
        stmt = stmt.where(HuntLog.criminal_id == criminal_id)
    return (await session.scalars(stmt)).all()


@router.get("/{hunt_id}/", response_model=HuntLogOut)
async def get_hunt(hunt_id: int, session: AsyncSession = Depends(get_session)):
    return await _get_hunt_or_404(session, hunt_id)


@router.post("/", response_model=HuntLogOut, status_code=status.HTTP_201_CREATED)
async def create_hunt(payload: HuntLogCreate, session: AsyncSession = Depends(get_session)):
    if await session.get(WantedCriminal, payload.criminal_id) is None:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, f"Criminal with id {payload.criminal_id} does not exist"
        )
    hunt = HuntLog(**payload.model_dump())
    session.add(hunt)
    await session.commit()
    await session.refresh(hunt)
    return hunt


@router.patch("/{hunt_id}/", response_model=HuntLogOut)
async def update_hunt(
    hunt_id: int, payload: HuntLogUpdate, session: AsyncSession = Depends(get_session)
):
    data = payload.model_dump(exclude_unset=True)
    if not data:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Provide 'success' and/or 'notes'")
    if any(value is None for value in data.values()):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Fields cannot be null")

    hunt = await _get_hunt_or_404(session, hunt_id)
    for field, value in data.items():
        setattr(hunt, field, value)
    await session.commit()
    await session.refresh(hunt)
    return hunt


@router.delete("/{hunt_id}/", status_code=status.HTTP_204_NO_CONTENT)
async def delete_hunt(hunt_id: int, session: AsyncSession = Depends(get_session)):
    hunt = await _get_hunt_or_404(session, hunt_id)
    await session.delete(hunt)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
