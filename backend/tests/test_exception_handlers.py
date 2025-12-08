import pytest
from unittest.mock import AsyncMock, patch
from fastapi import HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
import sqlalchemy.exc as sa_exc
from jose import JWTError

from app.core.exception_handlers import (
    http_exception_handler,
    validation_exception_handler,
    integrity_error_handler,
    sqlalchemy_error_handler,
    jwt_error_handler,
)


@pytest.fixture
def mock_request():
    request = AsyncMock(spec=Request)
    return request


@pytest.mark.asyncio
async def test_http_exception_handler(mock_request):
    exc = HTTPException(status_code=404, detail="Not found")
    response = await http_exception_handler(mock_request, exc)

    assert isinstance(response, JSONResponse)
    assert response.status_code == 404
    assert response.body == b'{"detail":"Not found"}'


@pytest.mark.asyncio
async def test_validation_exception_handler(mock_request):
    exc = RequestValidationError(
        errors=[{"msg": "Field required", "loc": ["body", "name"]}]
    )
    response = await validation_exception_handler(mock_request, exc)

    assert isinstance(response, JSONResponse)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert "Field required" in str(response.body)


@pytest.mark.asyncio
async def test_integrity_error_handler(mock_request):
    exc = sa_exc.IntegrityError("Duplicate key", None, None)
    exc.orig = Exception("UNIQUE constraint failed")

    with patch("app.core.exception_handlers.logger") as mock_logger:
        response = await integrity_error_handler(mock_request, exc)

    assert isinstance(response, JSONResponse)
    assert response.status_code == status.HTTP_409_CONFLICT
    assert "UNIQUE constraint failed" in str(response.body)
    mock_logger.exception.assert_called_once()


@pytest.mark.asyncio
async def test_sqlalchemy_error_handler(mock_request):
    exc = sa_exc.SQLAlchemyError("Database connection failed")

    with patch("app.core.exception_handlers.logger") as mock_logger:
        response = await sqlalchemy_error_handler(mock_request, exc)

    assert isinstance(response, JSONResponse)
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert "Database error" in str(response.body)
    mock_logger.exception.assert_called_once()


@pytest.mark.asyncio
async def test_jwt_error_handler(mock_request):
    exc = JWTError("Token expired")

    with patch("app.core.exception_handlers.logger") as mock_logger:
        response = await jwt_error_handler(mock_request, exc)

    assert isinstance(response, JSONResponse)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert "Invalid authentication token" in str(response.body)
    assert response.headers.get("WWW-Authenticate") == "Bearer"
    mock_logger.warning.assert_called_once()
