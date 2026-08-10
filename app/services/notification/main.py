"""Notification microservice entrypoint with a lifespan-managed SQS worker."""

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.shared.db import init_models
from app.services.notification import models  # noqa: F401 - register tables on Base
from app.services.notification.consumer import consume_forever
from app.services.notification.routes import router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("notification")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_models()
    stop_event = asyncio.Event()
    worker = asyncio.create_task(consume_forever(stop_event))
    logger.info("Notification SQS consumer started.")
    try:
        yield
    finally:
        stop_event.set()
        worker.cancel()
        try:
            await worker
        except asyncio.CancelledError:
            pass
        logger.info("Notification SQS consumer stopped.")


app = FastAPI(title="Notification Service", version="1.0.0", lifespan=lifespan)
app.include_router(router, tags=["notification"])


@app.get("/health", tags=["system"])
async def health():
    return {"status": "healthy", "service": "notification"}
