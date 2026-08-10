"""Payment routes: transaction registration + mock success states."""

import asyncio
import random
import uuid
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.db import get_db
from app.services.payment.models import Payment

router = APIRouter()

# Deterministic chaos trigger amount for failure-path demonstrations.
CHAOS_FAILURE_AMOUNT = 66.60


class PaymentRequest(BaseModel):
    order_id: int
    amount: Decimal


class PaymentResponse(BaseModel):
    status: str
    order_id: int
    amount: Decimal
    transaction_ref: str


async def _record(db: AsyncSession, *, order_id, amount, status_, ref) -> Payment:
    payment = Payment(order_id=order_id, amount=amount, status=status_, transaction_ref=ref)
    db.add(payment)
    await db.commit()
    await db.refresh(payment)
    return payment


@router.post("/payment/process", response_model=PaymentResponse, tags=["payment"])
async def process_payment(
    payload: PaymentRequest, db: AsyncSession = Depends(get_db)
) -> PaymentResponse:
    if float(payload.amount) == CHAOS_FAILURE_AMOUNT:
        await _record(db, order_id=payload.order_id, amount=payload.amount, status_="FAILED", ref=None)
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Simulated Gateway Error: Insufficient funds threshold met.",
        )

    await asyncio.sleep(random.uniform(0.2, 0.8))
    ref = f"txn_{uuid.uuid4().hex[:24]}"
    await _record(db, order_id=payload.order_id, amount=payload.amount, status_="SUCCESSFUL", ref=ref)
    return PaymentResponse(
        status="SUCCESSFUL",
        order_id=payload.order_id,
        amount=payload.amount,
        transaction_ref=ref,
    )


@router.get("/payment/transactions", tags=["payment"])
async def list_transactions(db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(select(Payment).order_by(Payment.id.desc()))).scalars().all()
    return [
        {
            "id": p.id,
            "order_id": p.order_id,
            "amount": str(p.amount),
            "status": p.status,
            "transaction_ref": p.transaction_ref,
        }
        for p in rows
    ]
