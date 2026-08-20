"""Notification routes: internal delivery-log inspection."""

from datetime import datetime

from app.services.notification.models import DeliveryLog
from app.shared.db import get_db
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()


class DeliveryLogOut(BaseModel):
    id: int
    message_id: str
    event_type: str
    order_id: int | None
    channel: str
    status: str
    payload: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


@router.get("/notification/logs", response_model=list[DeliveryLogOut], tags=["notification"])
async def list_logs(limit: int = 100, db: AsyncSession = Depends(get_db)) -> list[DeliveryLog]:
    stmt = select(DeliveryLog).order_by(DeliveryLog.id.desc()).limit(limit)
    return list((await db.execute(stmt)).scalars().all())
