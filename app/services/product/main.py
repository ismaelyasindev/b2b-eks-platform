"""Product microservice entrypoint."""

import logging
from contextlib import asynccontextmanager
from decimal import Decimal

from fastapi import FastAPI
from sqlalchemy import select

from app.shared.config import settings
from app.shared.db import SessionLocal, init_models
from app.services.product import models  # noqa: F401 - register tables on Base
from app.services.product.models import Product
from app.services.product.routes import router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("product")

# SKUs align with the frontend's retail translation layer (WIDGET/STORE/CDN/ENGINE).
SEED_PRODUCTS = [
    ("Enterprise Cloud Widget", "High-throughput modular automation block.", "B2B-WIDGET-001", Decimal("299.99"), 120),
    ("Managed Postgres Datastore", "Fully-managed relational storage cluster.", "DB-STORE-2002", Decimal("749.00"), 60),
    ("Global Edge CDN Node", "Low-latency content delivery node.", "NET-CDN-3003", Decimal("189.99"), 200),
    ("Compute Automation Engine", "Event-driven autoscaling workflow engine.", "CMP-ENGINE-4004", Decimal("1299.00"), 30),
    ("Object Storage Vault", "Durable versioned object storage buckets.", "DB-VAULT-5005", Decimal("349.50"), 150),
    ("Service Mesh Gateway", "Connected node-graph mesh gateway.", "NET-MESH-6006", Decimal("459.00"), 90),
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
