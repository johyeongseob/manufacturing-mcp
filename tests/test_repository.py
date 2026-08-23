"""Tests for observation repository queries and result mapping."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.asyncio import AsyncSession

from manufacturing_mcp.database.models import Observation
from manufacturing_mcp.database.repository import ObservationRepository


def compile_sql(statement) -> str:
    """Compile a SQLAlchemy statement as readable PostgreSQL SQL."""

    return str(
        statement.compile(
            dialect=postgresql.dialect(),
            compile_kwargs={"literal_binds": True},
        )
    )


async def test_get_by_udi_builds_single_observation_query() -> None:
    session = AsyncMock(spec=AsyncSession)
    result = MagicMock()
    observation = Observation(udi=1)
    result.scalar_one_or_none.return_value = observation
    session.execute.return_value = result

    returned = await ObservationRepository(session).get_by_udi(1)

    assert returned is observation
    sql = compile_sql(session.execute.await_args.args[0])
    assert "WHERE observations.udi = 1" in sql


async def test_list_all_orders_observations_by_udi() -> None:
    session = AsyncMock(spec=AsyncSession)
    result = MagicMock()
    result.scalars.return_value.all.return_value = [Observation(udi=1), Observation(udi=2)]
    session.execute.return_value = result

    returned = await ObservationRepository(session).list_all()

    assert [observation.udi for observation in returned] == [1, 2]
    sql = compile_sql(session.execute.await_args.args[0])
    assert "ORDER BY observations.udi" in sql
    assert "LIMIT" not in sql


async def test_search_applies_filters_order_and_limit() -> None:
    session = AsyncMock(spec=AsyncSession)
    result = MagicMock()
    result.scalars.return_value.all.return_value = [Observation(udi=10)]
    session.execute.return_value = result

    returned = await ObservationRepository(session).search(
        product_type="L",
        machine_failure=True,
        min_tool_wear=100,
        limit=25,
        offset=5,
    )

    assert [observation.udi for observation in returned] == [10]
    sql = compile_sql(session.execute.await_args.args[0])
    assert "observations.product_type = 'L'" in sql
    assert "observations.machine_failure IS true" in sql
    assert "observations.tool_wear >= 100" in sql
    assert "ORDER BY observations.udi" in sql
    assert "LIMIT 25 OFFSET 5" in sql


@pytest.mark.parametrize(
    ("arguments", "message"),
    [
        ({"product_type": "X"}, "product_type"),
        ({"min_tool_wear": -1}, "min_tool_wear"),
        ({"limit": 0}, "limit"),
        ({"limit": 501}, "limit"),
        ({"offset": -1}, "offset"),
    ],
)
async def test_search_rejects_invalid_filters(arguments, message: str) -> None:
    session = AsyncMock(spec=AsyncSession)

    with pytest.raises(ValueError, match=message):
        await ObservationRepository(session).search(**arguments)

    session.execute.assert_not_awaited()


async def test_get_failure_statistics_maps_aggregate_result() -> None:
    session = AsyncMock(spec=AsyncSession)
    result = MagicMock()
    result.mappings.return_value.one.return_value = {
        "total": 10_000,
        "failures": 339,
        "twf": 46,
        "hdf": 115,
        "pwf": 95,
        "osf": 98,
        "rnf": 19,
    }
    session.execute.return_value = result

    statistics = await ObservationRepository(session).get_failure_statistics()

    assert statistics.total == 10_000
    assert statistics.failures == 339
    assert statistics.failure_rate == pytest.approx(0.0339)
    assert statistics.hdf == 115
