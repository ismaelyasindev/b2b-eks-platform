"""Product routes: public catalog + internal stock checking."""

from decimal import Decimal

from app.services.product.models import Product
from app.shared.db import get_db
from app.shared.schemas import StockCheckRequest, StockCheckResponse, StockLine
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()


class ProductOut(BaseModel):
    id: int
    name: str
    description: str | None = None
    sku: str
    price: Decimal
    stock_quantity: int

    model_config = {"from_attributes": True}


# Strict single-prefix surface: every route lives under /product.
@router.get("/product/list", response_model=list[ProductOut], tags=["product"])
async def product_list(
    skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)
) -> list[Product]:
    stmt = select(Product).order_by(Product.id).offset(skip).limit(limit)
    return list((await db.execute(stmt)).scalars().all())


@router.get("/product/{product_id}", response_model=ProductOut, tags=["product"])
async def get_product(product_id: int, db: AsyncSession = Depends(get_db)) -> Product:
    product = await db.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    return product


@router.post("/product/check-stock", response_model=StockCheckResponse, tags=["product"])
async def check_stock(
    payload: StockCheckRequest, db: AsyncSession = Depends(get_db)
) -> StockCheckResponse:
    """Synchronous stock + price resolution for the order service."""
    ids = [i.product_id for i in payload.items]
    rows = (
        (await db.execute(select(Product).where(Product.id.in_(ids)))).scalars().all()
        if ids
        else []
    )
    by_id = {p.id: p for p in rows}

    lines: list[StockLine] = []
    ok = True
    for item in payload.items:
        product = by_id.get(item.product_id)
        if product is None:
            ok = False
            lines.append(
                StockLine(
                    product_id=item.product_id,
                    name="UNKNOWN",
                    sku="UNKNOWN",
                    price=Decimal("0.00"),
                    requested=item.quantity,
                    available_quantity=0,
                    in_stock=False,
                )
            )
            continue
        in_stock = product.stock_quantity >= item.quantity
        ok = ok and in_stock
        lines.append(
            StockLine(
                product_id=product.id,
                name=product.name,
                sku=product.sku,
                price=Decimal(str(product.price)),
                requested=item.quantity,
                available_quantity=product.stock_quantity,
                in_stock=in_stock,
            )
        )
    return StockCheckResponse(ok=ok, items=lines)
