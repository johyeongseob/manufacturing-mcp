"""Asynchronous PostgreSQL engine and session management."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from manufacturing_mcp.config import get_settings


def create_engine(database_url: str) -> AsyncEngine:
    """Create the application's asynchronous SQLAlchemy engine."""

    return create_async_engine(database_url, pool_pre_ping=True)


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """Create sessions bound to the supplied engine."""

    return async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        autoflush=False,
        expire_on_commit=False,
    )


engine = create_engine(get_settings().database_url)
AsyncSessionFactory = create_session_factory(engine)


@asynccontextmanager
async def session_scope() -> AsyncIterator[AsyncSession]:
    """Provide one session and roll back its transaction when an error occurs."""

    async with AsyncSessionFactory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


async def dispose_engine() -> None:
    """Release all pooled database connections during application shutdown."""

    await engine.dispose()
