"""Query operations for manufacturing observations."""

from dataclasses import dataclass
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from manufacturing_mcp.database.models import Observation


@dataclass(frozen=True)
class FailureStatistics:
    """Aggregated failure counts for all stored observations."""

    total: int
    failures: int
    failure_rate: float
    twf: int
    hdf: int
    pwf: int
    osf: int
    rnf: int


class ObservationRepository:
    """Read observations through one caller-provided database session."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_udi(self, udi: int) -> Observation | None:
        """Return one observation by UDI, or None when it does not exist."""

        statement = select(Observation).where(Observation.udi == udi)
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    async def list_all(self) -> list[Observation]:
        """Return every observation in UDI order for offline analysis."""

        statement = select(Observation).order_by(Observation.udi)
        result = await self._session.execute(statement)
        return list(result.scalars().all())

    async def search(
        self,
        *,
        product_type: str | None = None,
        machine_failure: bool | None = None,
        min_tool_wear: int | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Observation]:
        """Return observations matching optional filters in UDI order."""

        self._validate_search(product_type, min_tool_wear, limit, offset)

        statement = select(Observation)
        if product_type is not None:
            statement = statement.where(Observation.product_type == product_type)
        if machine_failure is not None:
            statement = statement.where(Observation.machine_failure.is_(machine_failure))
        if min_tool_wear is not None:
            statement = statement.where(Observation.tool_wear >= min_tool_wear)

        statement = statement.order_by(Observation.udi).limit(limit).offset(offset)
        result = await self._session.execute(statement)
        return list(result.scalars().all())

    async def get_failure_statistics(self) -> FailureStatistics:
        """Return total, overall failure, and failure-type counts."""

        statement = select(
            func.count().label("total"),
            self._true_count(Observation.machine_failure).label("failures"),
            self._true_count(Observation.twf).label("twf"),
            self._true_count(Observation.hdf).label("hdf"),
            self._true_count(Observation.pwf).label("pwf"),
            self._true_count(Observation.osf).label("osf"),
            self._true_count(Observation.rnf).label("rnf"),
        ).select_from(Observation)
        result = await self._session.execute(statement)
        row = result.mappings().one()

        total = int(row["total"])
        failures = int(row["failures"])
        return FailureStatistics(
            total=total,
            failures=failures,
            failure_rate=failures / total if total else 0.0,
            twf=int(row["twf"]),
            hdf=int(row["hdf"]),
            pwf=int(row["pwf"]),
            osf=int(row["osf"]),
            rnf=int(row["rnf"]),
        )

    @staticmethod
    def _true_count(column: Any):
        """Build a filtered count expression for a Boolean column."""

        return func.count().filter(column.is_(True))

    @staticmethod
    def _validate_search(
        product_type: str | None,
        min_tool_wear: int | None,
        limit: int,
        offset: int,
    ) -> None:
        if product_type is not None and product_type not in {"L", "M", "H"}:
            raise ValueError("product_type must be L, M, or H")
        if min_tool_wear is not None and min_tool_wear < 0:
            raise ValueError("min_tool_wear cannot be negative")
        if not 1 <= limit <= 500:
            raise ValueError("limit must be between 1 and 500")
        if offset < 0:
            raise ValueError("offset cannot be negative")
