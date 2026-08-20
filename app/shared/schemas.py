"""Common schemas & authentication token validation models.

The JWT principal is validated WITHOUT a database lookup so that any service
(e.g. order) can authenticate a caller without ever joining the auth schema —
preserving the distributed state boundary.
"""

from decimal import Decimal

import jwt
from app.shared.config import settings
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel, EmailStr

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token", auto_error=True)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenPrincipal(BaseModel):
    """Identity extracted purely from validated JWT claims."""

    user_id: int
    email: EmailStr
    tenant_id: int


class OrderItemIn(BaseModel):
    product_id: int
    quantity: int


class StockCheckRequest(BaseModel):
    items: list[OrderItemIn]


class StockLine(BaseModel):
    product_id: int
    name: str
    sku: str
    price: Decimal
    requested: int
    available_quantity: int
    in_stock: bool


class StockCheckResponse(BaseModel):
    ok: bool
    items: list[StockLine]


def decode_token(token: str) -> dict:
    return jwt.decode(
        token,
        settings.JWT_SECRET_KEY,
        algorithms=[settings.JWT_ALGORITHM],
    )


def get_current_principal(token: str = Depends(oauth2_scheme)) -> TokenPrincipal:
    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_token(token)
        return TokenPrincipal(
            user_id=int(payload["sub"]),
            email=payload["email"],
            tenant_id=int(payload["tenant_id"]),
        )
    except (jwt.PyJWTError, KeyError, ValueError, TypeError):
        raise credentials_exc
