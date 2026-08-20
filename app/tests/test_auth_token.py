import jwt
import pytest
from app.shared.config import settings
from app.shared.schemas import get_current_principal
from fastapi import HTTPException


def test_valid_token_returns_principal():
    token = jwt.encode(
        {
            "sub": "42",
            "email": "buyer@company.com",
            "tenant_id": 7,
        },
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )

    principal = get_current_principal(token)

    assert principal.user_id == 42
    assert principal.email == "buyer@company.com"
    assert principal.tenant_id == 7


def test_invalid_token_returns_unauthorized():
    with pytest.raises(HTTPException) as error:
        get_current_principal("invalid-token")

    assert error.value.status_code == 401
