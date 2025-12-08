import sys
import os

# Add the project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../")))

import asyncio

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.database.models import Base
from app.main import app

DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def engine():
    engine = create_async_engine(DATABASE_URL, future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture()
async def db_session(engine):
    AsyncSessionLocal = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    async with AsyncSessionLocal() as session:
        yield session


@pytest_asyncio.fixture(autouse=True)
async def override_dependencies(db_session):
    # Override get_db
    async def _get_db():
        async with db_session.begin():
            yield db_session

    app.dependency_overrides.clear()
    # override get_db in modules that declare it
    from app.auth.firebase_auth import get_db as auth_get_db
    from app.routes.post_routes import get_db as post_get_db
    from app.routes.thread_routes import get_db as thread_get_db
    from app.routes.ws_routes import get_db as ws_get_db

    for fn in (auth_get_db, post_get_db, thread_get_db, ws_get_db):
        app.dependency_overrides[fn] = _get_db

    yield

    app.dependency_overrides.clear()
