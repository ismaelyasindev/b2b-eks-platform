"""Auth microservice entrypoint."""

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from passlib.context import CryptContext
from sqlalchemy import select

from app.shared.config import settings
from app.shared.db import SessionLocal, init_models
from app.services.auth import models  # noqa: F401 - register tables on Base
from app.services.auth.models import Tenant, User
from app.services.auth.routes import router
from app.services.auth.core.throttle_manager import manager, throttle_enabled

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("auth")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


async def _seed_local() -> None:
    async with SessionLocal() as db:
        existing = (await db.execute(select(Tenant))).scalars().first()
        if existing is not None:
            return
        tenant = Tenant(name="Acme Global Tech", plan="enterprise")
        db.add(tenant)
        await db.flush()
        db.add(
            User(
                email="recruiter@company.com",
                hashed_password=pwd_context.hash("password123"),
                tenant_id=tenant.id,
                is_active=True,
            )
        )
        await db.commit()
        logger.info("Seeded tenant 'Acme Global Tech' and recruiter user.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_models()
    if settings.ENVIRONMENT == "local":
        try:
            await _seed_local()
        except Exception as exc:  # noqa: BLE001
            logger.warning("Auth seed skipped/failed: %s", exc)

    # AIOps remediation enforcement: poll the DynamoDB throttle flag into memory.
    # The middleware below reacts to whatever this populates; if the poller is
    # disabled (local mode) active_throttles stays empty and the middleware no-ops.
    stop_event = asyncio.Event()
    poller: asyncio.Task | None = None
    if throttle_enabled():
        poller = asyncio.create_task(manager.poll_forever(stop_event))
        logger.info("Throttle poller started (table=%s).", manager.table_name)
    else:
        logger.info("Throttle poller disabled (no Secrets Manager creds / THROTTLE_ENABLED unset).")

    try:
        yield
    finally:
        stop_event.set()
        if poller is not None:
            poller.cancel()
            try:
                await poller
            except asyncio.CancelledError:
                pass
            logger.info("Throttle poller stopped.")


app = FastAPI(title="Auth Service", version="1.0.0", lifespan=lifespan)


@app.middleware("http")
async def emergency_throttle(request: Request, call_next):
    # Returns 429 only when the AIOps Lambda has written an active throttle flag
    # for this exact path (e.g. /auth/signup). A no-op for every other request.
    if manager.is_blocked(request.url.path):
        return JSONResponse(
            status_code=429,
            content={"detail": "Emergency throttle active. Please retry shortly."},
        )
    return await call_next(request)


app.include_router(router, prefix="/auth", tags=["auth"])


@app.get("/health", tags=["system"])
async def health():
    return {"status": "healthy", "service": "auth"}
