"""Order microservice entrypoint."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.shared.db import init_models
from app.services.order import models  # noqa: F401 - register tables on Base
from app.services.order.routes import router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("order")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_models()
    yield


app = FastAPI(title="Order Service", version="1.0.0", lifespan=lifespan)
app.include_router(router, tags=["order"])


@app.get("/health", tags=["system"])
async def health():
    return {"status": "healthy", "service": "order"}
