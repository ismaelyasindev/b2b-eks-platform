"""Dynamic database engine factory and credential manager.

Credential sourcing is fully decoupled from disk:
  * local  -> read injected env vars (docker-compose)
  * AWS     -> fetch the JSON secret from Secrets Manager via EKS Pod Identity

Every service binds to a single Postgres schema (search_path) and a
schema-scoped role, enforcing the "zero cross-service join" boundary at the
role-and-grant layer.
"""

import json
import os
from collections.abc import AsyncGenerator

import boto3
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import declarative_base

# Shared declarative base. Because each service process imports only its own
# `models` module, `Base.metadata` only ever contains that service's tables.
Base = declarative_base()


def _db_credentials() -> dict:
    """
    Local: reads password directly from environment variables injected by docker-compose.
    AWS:   reads the JSON secret from Secrets Manager using EKS Pod Identity credentials.
    Controlled by the DB_CREDENTIALS_SOURCE environment variable.
    """
    if os.environ.get("DB_CREDENTIALS_SOURCE", "env") == "secretsmanager":
        sm = boto3.client(
            "secretsmanager",
            region_name=os.environ.get("AWS_DEFAULT_REGION", "eu-west-2"),
        )
        secret = sm.get_secret_value(SecretId=os.environ["DB_SECRET_ID"])
        return json.loads(secret["SecretString"])
    return {
        "username": os.environ["DB_USER"],
        "password": os.environ["DB_PASSWORD"],
        "host": os.environ["DB_HOST"],
        "port": os.environ.get("DB_PORT", "5432"),
        "dbname": os.environ["DB_NAME"],
    }


def make_engine() -> AsyncEngine:
    c = _db_credentials()
    schema = os.environ["DB_SCHEMA"]
    url = f"postgresql+asyncpg://{c['username']}:{c['password']}@{c['host']}:{c['port']}/{c['dbname']}"

    return create_async_engine(
        url,
        pool_size=int(os.environ.get("DB_POOL_SIZE", "5")),
        max_overflow=int(os.environ.get("DB_MAX_OVERFLOW", "10")),
        pool_pre_ping=True,
        connect_args={"server_settings": {"search_path": schema}},
    )


# Engine / session factory are created lazily per process at import time.
engine: AsyncEngine = make_engine()
SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency yielding a scoped async session."""
    async with SessionLocal() as session:
        yield session


async def init_models() -> None:
    """Create this service's tables (idempotent). The schema itself is created
    by the db init script; this only materializes tables inside it."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
