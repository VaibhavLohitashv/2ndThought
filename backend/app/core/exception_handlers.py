import logging

import sqlalchemy.exc as sa_exc
from fastapi import HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from jose import JWTError

logger = logging.getLogger("uvicorn.error")


async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": exc.errors()},
    )


async def integrity_error_handler(request: Request, exc: sa_exc.IntegrityError):
    logger.exception("Database integrity error: %s", exc)
    detail = None
    try:
        detail = str(exc.orig)
    except Exception:
        detail = str(exc)
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT, content={"detail": detail}
    )


async def sqlalchemy_error_handler(request: Request, exc: sa_exc.SQLAlchemyError):
    logger.exception("Database error: %s", exc)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Database error"},
    )


async def jwt_error_handler(request: Request, exc: JWTError):
    logger.warning("JWT error: %s", exc)
    return JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content={"detail": "Invalid authentication token"},
        headers={"WWW-Authenticate": "Bearer"},
    )


async def value_error_handler(request: Request, exc: ValueError):
    logger.warning("Value error: %s", exc)
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST, content={"detail": str(exc)}
    )


async def generic_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled exception: %s", exc)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"},
    )


def register_exception_handlers(app):
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(sa_exc.IntegrityError, integrity_error_handler)
    app.add_exception_handler(sa_exc.SQLAlchemyError, sqlalchemy_error_handler)
    app.add_exception_handler(JWTError, jwt_error_handler)
    app.add_exception_handler(ValueError, value_error_handler)
    app.add_exception_handler(Exception, generic_exception_handler)
