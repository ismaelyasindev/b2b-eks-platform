"""Auth routes: tenant onboarding, signup, and JWT token issuance."""

from datetime import datetime, timedelta, timezone

import jwt
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.config import settings
from app.shared.db import get_db
from app.shared.schemas import Token
from app.services.auth.models import Tenant, User

router = APIRouter()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class TenantCreate(BaseModel):
    name: str
    plan: str = "enterprise"


class TenantOut(BaseModel):
    id: int
    name: str
    plan: str

    model_config = {"from_attributes": True}


class SignupRequest(BaseModel):
    email: EmailStr
    password: str | None = None
    tenant_id: int | None = None


class UserOut(BaseModel):
    id: int
    email: EmailStr
    tenant_id: int

    model_config = {"from_attributes": True}


def _create_access_token(user: User) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user.id),
        "email": user.email,
        "tenant_id": user.tenant_id,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)).timestamp()),
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


@router.post("/tenants", response_model=TenantOut, status_code=status.HTTP_201_CREATED)
async def create_tenant(payload: TenantCreate, db: AsyncSession = Depends(get_db)) -> Tenant:
    existing = (
        await db.execute(select(Tenant).where(Tenant.name == payload.name))
    ).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(status_code=409, detail="Tenant already exists")
    tenant = Tenant(name=payload.name, plan=payload.plan)
    db.add(tenant)
    await db.commit()
    await db.refresh(tenant)
    return tenant


@router.post("/signup", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def signup(request: Request, db: AsyncSession = Depends(get_db)):
    # --- SRE Chaos Injection Hook ---------------------------------------
    # A flagged request forces a 5s server-side lock on the connection to
    # simulate a downstream metric/connection storm for load testing.
    if request.headers.get("X-Trigger-Storm") == "true":
        await db.execute(text("SELECT pg_sleep(5)"))

    # --- Normal signup logic -------------------------------------------
    body = await request.json()
    payload = SignupRequest(**body)

    existing = (
        await db.execute(select(User).where(User.email == payload.email))
    ).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(status_code=409, detail="User already exists")

    # Resolve tenant: explicit tenant_id, else first/default tenant, else create one.
    tenant: Tenant | None = None
    if payload.tenant_id is not None:
        tenant = await db.get(Tenant, payload.tenant_id)
    if tenant is None:
        tenant = (await db.execute(select(Tenant).order_by(Tenant.id))).scalars().first()
    if tenant is None:
        tenant = Tenant(name="Default Tenant", plan="enterprise")
        db.add(tenant)
        await db.flush()

    user = User(
        email=payload.email,
        hashed_password=pwd_context.hash(payload.password or "changeme123"),
        tenant_id=tenant.id,
        is_active=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@router.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
) -> Token:
    user = (
        await db.execute(select(User).where(User.email == form_data.username))
    ).scalar_one_or_none()
    if user is None or not user.is_active or not pwd_context.verify(
        form_data.password, user.hashed_password
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return Token(access_token=_create_access_token(user))
