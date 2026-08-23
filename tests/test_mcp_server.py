"""Tests for the manufacturing MCP server and its first tool."""

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock

import pytest

from manufacturing_mcp.database.models import Observation
from manufacturing_mcp.mcp_server import server as server_module


def sample_observation() -> Observation:
    """Return one complete observation for tool serialization tests."""

    return Observation(
        udi=1,
        product_id="M14860",
        product_type="M",
        air_temperature=298.1,
        process_temperature=308.6,
        rotational_speed=1551,
        torque=42.8,
        tool_wear=0,
        machine_failure=False,
        twf=False,
        hdf=False,
        pwf=False,
        osf=False,
        rnf=False,
    )


async def test_get_observation_returns_structured_result(monkeypatch) -> None:
    session = AsyncMock()

    @asynccontextmanager
    async def fake_session_scope():
        yield session

    repository = AsyncMock()
    repository.get_by_udi.return_value = sample_observation()
    monkeypatch.setattr(server_module, "session_scope", fake_session_scope)
    monkeypatch.setattr(server_module, "ObservationRepository", lambda _: repository)

    result = await server_module.get_observation(1)

    assert result.found is True
    assert result.product_id == "M14860"
    assert result.machine_failure is False
    assert result.failure_types == []
    repository.get_by_udi.assert_awaited_once_with(1)


async def test_get_observation_reports_missing_udi(monkeypatch) -> None:
    @asynccontextmanager
    async def fake_session_scope():
        yield AsyncMock()

    repository = AsyncMock()
    repository.get_by_udi.return_value = None
    monkeypatch.setattr(server_module, "session_scope", fake_session_scope)
    monkeypatch.setattr(server_module, "ObservationRepository", lambda _: repository)

    result = await server_module.get_observation(99_999)

    assert result.found is False
    assert result.udi == 99_999


async def test_get_observation_rejects_non_positive_udi() -> None:
    with pytest.raises(ValueError, match="positive"):
        await server_module.get_observation(0)


async def test_search_observations_returns_limited_rows(monkeypatch) -> None:
    @asynccontextmanager
    async def fake_session_scope():
        yield AsyncMock()

    repository = AsyncMock()
    repository.search.return_value = [sample_observation()]
    monkeypatch.setattr(server_module, "session_scope", fake_session_scope)
    monkeypatch.setattr(server_module, "ObservationRepository", lambda _: repository)

    result = await server_module.search_observations(machine_failure=True, limit=2)

    assert result.count == 1
    assert result.observations[0].udi == 1
    repository.search.assert_awaited_once_with(
        product_type=None,
        machine_failure=True,
        min_tool_wear=None,
        limit=2,
    )


async def test_search_observations_rejects_large_limit() -> None:
    with pytest.raises(ValueError, match="between 1 and 20"):
        await server_module.search_observations(limit=21)


async def test_server_registers_postgres_tools() -> None:
    tools = await server_module.server.list_tools()

    assert [tool.name for tool in tools] == ["get_observation", "search_observations"]
