import os
from uuid import uuid4
from typing import AsyncGenerator
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlmodel import SQLModel

# Set TESTING environment variable before importing settings
os.environ["TESTING"] = "True"

from src.apps.core.config import Settings
from src.db import session as db_session_module
from src.db.session import get_session
from src.main import app


@pytest.fixture(autouse=True)
async def reset_in_memory_runtime_state():
    from src.apps.iam import security as iam_security
    from src.apps.core.cache import RedisCache

    iam_security._IN_MEMORY_POLICY_OVERRIDES.clear()
    iam_security._IN_MEMORY_STEP_UP_STORE.clear()
    iam_security._IN_MEMORY_STEP_UP_MARKERS.clear()
    await RedisCache.close()
    yield
    iam_security._IN_MEMORY_POLICY_OVERRIDES.clear()
    iam_security._IN_MEMORY_STEP_UP_STORE.clear()
    iam_security._IN_MEMORY_STEP_UP_MARKERS.clear()
    await RedisCache.close()


@pytest.fixture(scope="function")
async def test_engine():
    """Create a test engine for each test function with a unique PostgreSQL database."""
    settings = Settings()
    database_name = f"test_{uuid4().hex}"
    admin_url = make_url(settings.SYNC_DATABASE_URL).set(database="postgres")
    test_async_url = make_url(settings.DATABASE_URL).set(database=database_name)
    admin_engine = create_engine(admin_url, isolation_level="AUTOCOMMIT")
    quoted_database_name = database_name.replace('"', '""')

    with admin_engine.connect() as connection:
        connection.execute(
            text("SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = :database"),
            {"database": database_name},
        )
        connection.exec_driver_sql(f'CREATE DATABASE "{quoted_database_name}"')

    engine = create_async_engine(test_async_url, echo=False)

    try:
        async with engine.begin() as conn:
            await conn.run_sync(SQLModel.metadata.create_all)

        yield engine
    finally:
        async with engine.begin() as conn:
            await conn.run_sync(SQLModel.metadata.drop_all)
        await engine.dispose()
        with admin_engine.connect() as connection:
            connection.execute(
                text("SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = :database"),
                {"database": database_name},
            )
            connection.exec_driver_sql(f'DROP DATABASE IF EXISTS "{quoted_database_name}"')
        admin_engine.dispose()


@pytest.fixture(scope="function")
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create a fresh database session for each test."""
    async_session = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False
    )

    async with async_session() as session:
        yield session


@pytest.fixture(scope="function")
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create a test client with database session override and disabled rate limiting."""
    from src import main as main_module
    from src.apps.iam.api.deps import get_db
    from src.apps.analytics.service import AnalyticsService
    from src.apps.analytics.dependencies import get_analytics

    test_async_session = async_sessionmaker(
        db_session.bind,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        async with test_async_session() as session:
            yield session

    # Provide a disabled (no-op) analytics service for tests
    _noop_analytics = AnalyticsService(provider=None)
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_session] = override_get_db
    app.dependency_overrides[get_analytics] = lambda: _noop_analytics

    original_engine = db_session_module.engine
    original_main_engine = main_module.engine
    original_async_session_factory = db_session_module.async_session_factory
    db_session_module.engine = db_session.bind
    main_module.engine = db_session.bind
    db_session_module.async_session_factory = test_async_session

    # Disable rate limiting for tests - handle both main limiter and route limiters
    if hasattr(app.state, 'limiter'):
        original_enabled = app.state.limiter.enabled
        app.state.limiter.enabled = False
    else:
        original_enabled = None

    # Also disable limiters in individual route modules
    limiters_to_restore = []
    try:
        from src.apps.iam.api.v1.auth import signup, login, password
        for module in [signup, login, password]:
            if hasattr(module, 'limiter'):
                limiters_to_restore.append((module.limiter, module.limiter.enabled))
                module.limiter.enabled = False
    except Exception:
        pass

    # Mock email service to avoid sending real emails
    with patch("src.apps.iam.services.email.EmailService.send_welcome_email", new_callable=AsyncMock):
        with patch("src.apps.iam.services.email.EmailService.send_verification_email", new_callable=AsyncMock):
            with patch("src.apps.iam.services.email.EmailService.send_password_reset_email", new_callable=AsyncMock):
                async with AsyncClient(
                    transport=ASGITransport(app=app),
                    base_url="http://test"
                ) as test_client:
                    yield test_client

    # Restore rate limiting after test
    if original_enabled is not None:
        app.state.limiter.enabled = original_enabled

    # Restore module limiters
    for limiter, was_enabled in limiters_to_restore:
        limiter.enabled = was_enabled

    db_session_module.engine = original_engine
    main_module.engine = original_main_engine
    db_session_module.async_session_factory = original_async_session_factory
    app.dependency_overrides.clear()
