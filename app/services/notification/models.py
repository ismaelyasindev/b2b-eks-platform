"""Notification domain models (notification_schema).

`delivery_logs` doubles as the idempotency ledger: a UNIQUE message_id lets the
consumer detect and skip duplicate SQS deliveries (at-least-once semantics).
"""

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.db import Base

SCHEMA = "notification_schema"


class DeliveryLog(Base):
    __tablename__ = "delivery_logs"
    __table_args__ = {"schema": SCHEMA}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    message_id: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    order_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    channel: Mapped[str] = mapped_column(String(32), nullable=False, default="email")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="SENT")
    payload: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
