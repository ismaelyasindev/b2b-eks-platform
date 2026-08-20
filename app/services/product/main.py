"""Product microservice entrypoint."""

import logging
from contextlib import asynccontextmanager
from decimal import Decimal

from app.services.product import models  # noqa: F401 - register tables on Base
from app.services.product.models import Product
from app.services.product.routes import router
from app.shared.config import settings
from app.shared.db import SessionLocal, init_models
from fastapi import FastAPI
from sqlalchemy import select

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("product")

SEED_PRODUCTS = [
    ("Stretch Pallet Wrap (23µm, 400m)", "Machine-grade LLDPE wrap for outbound palletising. Sold per roll.", "WH-PKG-1001", Decimal("28.50"), 500),
    ("Nitrile Exam Gloves (Box of 100)", "Powder-free, ambidextrous, size L. Wholesale carton pricing on request.", "WH-PPE-2002", Decimal("12.40"), 2000),
    ("Stainless Steel Boltless Shelving", "1800×900×400 mm, 5 levels, 200 kg/shelf. Flat-packed for depot delivery.", "WH-FUR-3003", Decimal("189.00"), 80),
    ("LED High-Bay Light 150W", "IP65 warehouse fitting, 4000K, 140 lm/W. Includes mounting bracket.", "WH-ELC-4004", Decimal("74.00"), 350),
    ("Food-Grade HDPE Drum 60L", "UN-rated, tamper-evident lid, stackable. Suitable for dry goods.", "WH-CNT-5005", Decimal("36.00"), 600),
    ("Desktop Barcode Label Printer", "203 dpi thermal transfer, 4-inch media, USB + Ethernet. Labels sold separately.", "WH-IT-6006", Decimal("249.00"), 45),
]


async def _seed_local() -> None:
    async with SessionLocal() as db:
        existing = (await db.execute(select(Product))).scalars().first()
        if existing is not None:
            return
        db.add_all(
            Product(name=n, description=d, sku=s, price=p, stock_quantity=q)
            for (n, d, s, p, q) in SEED_PRODUCTS
        )
        await db.commit()
        logger.info("Seeded %d products.", len(SEED_PRODUCTS))


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_models()
    if settings.ENVIRONMENT == "local":
        try:
            await _seed_local()
        except Exception as exc:  # noqa: BLE001
            logger.warning("Product seed skipped/failed: %s", exc)
    yield


app = FastAPI(title="Product Service", version="1.0.0", lifespan=lifespan)
app.include_router(router, tags=["product"])


@app.get("/health", tags=["system"])
async def health():
    return {"status": "healthy", "service": "product"}
