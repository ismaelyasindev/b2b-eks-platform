"""Order routes: checkout with synchronous stock-check + async SQS publish."""

import json
import logging
from decimal import Decimal

import boto3
import httpx
from app.services.order.models import Order, OrderItem, OrderStatus
from app.shared.config import settings
from app.shared.db import get_db
from app.shared.schemas import TokenPrincipal, get_current_principal
from botocore.exceptions import BotoCoreError, ClientError
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger("order")
router = APIRouter()


class OrderItemIn(BaseModel):
    product_id: int
    quantity: int = Field(gt=0)


class CreateOrderRequest(BaseModel):
    items: list[OrderItemIn]


class OrderItemOut(BaseModel):
    product_id: int
    quantity: int
    price: Decimal

    model_config = {"from_attributes": True}


class OrderOut(BaseModel):
    id: int
    tenant_id: int
    user_id: int
    status: str
    total_amount: Decimal
    items: list[OrderItemOut]

    model_config = {"from_attributes": True}


def _sqs_client():
    return boto3.client(
        "sqs",
        region_name=settings.AWS_DEFAULT_REGION,
        endpoint_url=settings.AWS_ENDPOINT_URL,
    )


def _publish_order_completed(order: Order) -> None:
    """Serialize transaction metadata and publish OrderCompleted to SQS.

    Honours AWS_ENDPOINT_URL so it routes to LocalStack locally. Never raises
    into the request path — a messaging failure must not fail a committed order.
    """
    try:
        sqs = _sqs_client()
        queue_url = sqs.create_queue(QueueName=settings.SQS_QUEUE_NAME)["QueueUrl"]
        message = {
            "event_type": "OrderCompleted",
            "order_id": order.id,
            "tenant_id": order.tenant_id,
            "user_id": order.user_id,
            "total_amount": str(order.total_amount),
            "items": [
                {"product_id": i.product_id, "quantity": i.quantity, "price": str(i.price)}
                for i in order.items
            ],
        }
        sqs.send_message(QueueUrl=queue_url, MessageBody=json.dumps(message))
        logger.info("Published OrderCompleted for order %s", order.id)
    except (BotoCoreError, ClientError, KeyError) as exc:
        logger.warning("SQS publish skipped for order %s: %s", order.id, exc)


async def _check_stock(items: list[OrderItemIn]) -> dict[int, dict]:
    """Synchronous stock check against the product service (strict 2s timeout).

    Fails fast with 503 if the dependency is slow or unavailable.
    """
    url = f"{settings.PRODUCT_SERVICE_URL}/product/check-stock"
    payload = {"items": [item.model_dump() for item in items]}
    try:
        async with httpx.AsyncClient(timeout=settings.PRODUCT_STOCK_TIMEOUT_SECONDS) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
    except (httpx.TimeoutException, httpx.TransportError) as exc:
        logger.error("Product stock-check unreachable: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Product service unavailable (stock check failed)",
        )
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Product service error during stock check: {exc.response.status_code}",
        )

    data = resp.json()
    return {line["product_id"]: line for line in data["items"]}


@router.post(
    "/order",
    response_model=OrderOut,
    status_code=status.HTTP_201_CREATED,
    tags=["order"],
)
async def create_order(
    payload: CreateOrderRequest,
    db: AsyncSession = Depends(get_db),
    principal: TokenPrincipal = Depends(get_current_principal),
) -> Order:
    if not payload.items:
        raise HTTPException(status_code=400, detail="An order must contain at least one item.")

    stock = await _check_stock(payload.items)

    total = Decimal("0.00")
    order = Order(
        tenant_id=principal.tenant_id,
        user_id=principal.user_id,
        status=OrderStatus.PAID.value,
        total_amount=Decimal("0.00"),
    )
    for item in payload.items:
        line = stock.get(item.product_id)
        if line is None or not line["in_stock"]:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Insufficient stock for product {item.product_id}",
            )
        price = Decimal(str(line["price"]))
        total += price * item.quantity
        order.items.append(
            OrderItem(product_id=item.product_id, quantity=item.quantity, price=price)
        )

    order.total_amount = total
    db.add(order)
    await db.commit()
    await db.refresh(order)
    # Eager-load items for the response + SQS payload.
    await db.refresh(order, attribute_names=["items"])

    _publish_order_completed(order)
    return order


@router.get("/order", response_model=list[OrderOut], tags=["order"])
async def list_orders(
    db: AsyncSession = Depends(get_db),
    principal: TokenPrincipal = Depends(get_current_principal),
) -> list[Order]:
    stmt = (
        select(Order)
        .where(Order.tenant_id == principal.tenant_id)
        .order_by(Order.id.desc())
    )
    return list((await db.execute(stmt)).scalars().unique().all())


@router.get("/order/{order_id}", response_model=OrderOut, tags=["order"])
async def get_order(
    order_id: int,
    db: AsyncSession = Depends(get_db),
    principal: TokenPrincipal = Depends(get_current_principal),
) -> Order:
    order = await db.get(Order, order_id)
    if order is None or order.tenant_id != principal.tenant_id:
        raise HTTPException(status_code=404, detail="Order not found")
    await db.refresh(order, attribute_names=["items"])
    return order
