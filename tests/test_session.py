"""Tests for asynchronous database session configuration."""

from sqlalchemy.ext.asyncio import AsyncSession

from manufacturing_mcp.database.session import create_engine, create_session_factory


def test_create_engine_uses_async_postgresql_driver() -> None:
    engine = create_engine("postgresql+asyncpg://user:password@localhost/database")

    assert engine.url.drivername == "postgresql+asyncpg"
    assert engine.pool._pre_ping is True


async def test_session_factory_creates_async_session() -> None:
    engine = create_engine("postgresql+asyncpg://user:password@localhost/database")
    factory = create_session_factory(engine)

    async with factory() as session:
        assert isinstance(session, AsyncSession)
        assert session.sync_session.autoflush is False
        assert session.sync_session.expire_on_commit is False

    await engine.dispose()
