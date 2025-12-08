import pytest
from unittest.mock import AsyncMock, patch
from fastapi import HTTPException
from app.core.security import get_current_user, get_db
from app.auth.jwt import decode_access_token
from app.database.models import User

# Mock database session
@pytest.fixture
def mock_db():
    mock_session = AsyncMock()
    yield mock_session

# Mock token decoding
@pytest.fixture
def mock_decode_token():
    with patch("app.auth.jwt.decode_access_token") as mock:
        yield mock

@pytest.mark.asyncio
async def test_get_current_user_valid_token(mock_db, mock_decode_token):
    mock_decode_token.return_value = {"sub": "test@example.com"}
    mock_db.execute.return_value.scalar_one_or_none.return_value = User(email="test@example.com")

    user = await get_current_user(token="valid_token", db=mock_db)
    assert user.email == "test@example.com"

@pytest.mark.asyncio
async def test_get_current_user_invalid_token(mock_db, mock_decode_token):
    mock_decode_token.return_value = None

    with pytest.raises(HTTPException) as exc:
        await get_current_user(token="invalid_token", db=mock_db)

    assert exc.value.status_code == 401
    assert exc.value.detail == "Could not validate credentials"

@pytest.mark.asyncio
async def test_get_current_user_no_user_in_db(mock_db, mock_decode_token):
    mock_decode_token.return_value = {"sub": "test@example.com"}
    mock_db.execute.return_value.scalar_one_or_none.return_value = None

    with pytest.raises(HTTPException) as exc:
        await get_current_user(token="valid_token", db=mock_db)

    assert exc.value.status_code == 401
    assert exc.value.detail == "Could not validate credentials"