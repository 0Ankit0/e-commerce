from collections.abc import Mapping
from datetime import UTC, datetime
from typing import AsyncGenerator
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import AsyncAdaptedQueuePool
from sqlmodel import SQLModel
from src.apps.core.config import settings
from src.apps.core.settings_store import sync_general_settings

if not settings.DATABASE_URL:
    raise ValueError("DATABASE_URL is not set in the configuration")

engine_kwargs: dict[str, object] = {
    "url": settings.DATABASE_URL,
    "echo": settings.LOG_SQL_QUERIES,
    "future": True,
    "poolclass": AsyncAdaptedQueuePool,
    "pool_size": settings.DB_POOL_SIZE,
    "max_overflow": settings.DB_MAX_OVERFLOW,
    "pool_timeout": settings.DB_POOL_TIMEOUT,
    "pool_recycle": settings.DB_POOL_RECYCLE,
}

engine = create_async_engine(**engine_kwargs)


def _normalize_datetime_value(value: object) -> object:
    if isinstance(value, datetime) and value.tzinfo is not None and value.tzinfo.utcoffset(value) is not None:
        return value.astimezone(UTC).replace(tzinfo=None)
    if isinstance(value, Mapping):
        return {key: _normalize_datetime_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_normalize_datetime_value(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_normalize_datetime_value(item) for item in value)
    return value


@event.listens_for(engine.sync_engine, "before_cursor_execute", retval=True)
def _normalize_aware_datetime_parameters(
    conn,
    cursor,
    statement,
    parameters,
    context,
    executemany,
):
    return statement, _normalize_datetime_value(parameters)

async_session_factory = async_sessionmaker(engine, expire_on_commit=False)

async def init_db():
    # Import all models so SQLModel.metadata knows about every table
    import src.apps.core.models  # noqa: F401
    import src.apps.iam.models  # noqa: F401
    import src.apps.notification.models  # noqa: F401
    import src.apps.multitenancy.models  # noqa: F401
    import src.apps.finance.models  # noqa: F401
    import src.apps.websocket.models  # noqa: F401
    import src.apps.observability.models  # noqa: F401
    import src.apps.vendors.models  # noqa: F401
    import src.apps.catalog.models  # noqa: F401
    import src.apps.commerce.models  # noqa: F401
    import src.apps.promotions.models  # noqa: F401
    import src.apps.orders.models  # noqa: F401
    import src.apps.recommendations.models  # noqa: F401
    import src.apps.logistics.models  # noqa: F401
    import src.apps.messaging.models  # noqa: F401
    import src.apps.support.models  # noqa: F401
    import src.apps.communications.models  # noqa: F401

    if settings.TESTING:
        async with engine.begin() as conn:
            await conn.run_sync(SQLModel.metadata.create_all)

    async with async_session_factory() as session:
        await sync_general_settings(session)

async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        yield session
