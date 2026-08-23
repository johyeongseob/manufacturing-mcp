"""MCP server for querying manufacturing observations."""

from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field

from manufacturing_mcp.database.repository import ObservationRepository
from manufacturing_mcp.database.session import session_scope

server = FastMCP(
    "manufacturing-mcp",
    instructions="PostgreSQL에 저장된 제조 설비 관측값을 조회합니다.",
)


class ObservationResult(BaseModel):
    """Structured result returned by the observation lookup tool."""

    found: bool
    udi: int
    product_id: str | None = None
    product_type: str | None = None
    air_temperature: float | None = None
    process_temperature: float | None = None
    rotational_speed: int | None = None
    torque: float | None = None
    tool_wear: int | None = None
    machine_failure: bool | None = None
    failure_types: list[str] = Field(default_factory=list)


class ObservationSearchResult(BaseModel):
    """Structured collection returned by the observation search tool."""

    count: int
    observations: list[ObservationResult]


@server.tool(
    name="get_observation",
    title="Get manufacturing observation",
    description="UDI로 제조 설비 관측값과 고장 여부를 한 건 조회합니다.",
    structured_output=True,
)
async def get_observation(udi: int) -> ObservationResult:
    """Return one PostgreSQL observation identified by its positive UDI."""

    if udi <= 0:
        raise ValueError("udi must be a positive integer")

    async with session_scope() as session:
        observation = await ObservationRepository(session).get_by_udi(udi)

    if observation is None:
        return ObservationResult(found=False, udi=udi)

    return _serialize_observation(observation)


@server.tool(
    name="search_observations",
    title="Search manufacturing observations",
    description=(
        "제품 등급, 설비 고장 여부, 최소 공구 마모 시간으로 PostgreSQL 원본 관측값을 "
        "검색합니다. 실제 행이나 고장 샘플을 요청할 때 사용합니다."
    ),
    structured_output=True,
)
async def search_observations(
    product_type: str | None = None,
    machine_failure: bool | None = None,
    min_tool_wear: int | None = None,
    limit: int = 5,
) -> ObservationSearchResult:
    """Return a small, read-only sample of observations matching safe filters."""

    if not 1 <= limit <= 20:
        raise ValueError("limit must be between 1 and 20")

    async with session_scope() as session:
        observations = await ObservationRepository(session).search(
            product_type=product_type,
            machine_failure=machine_failure,
            min_tool_wear=min_tool_wear,
            limit=limit,
        )
    rows = [_serialize_observation(observation) for observation in observations]
    return ObservationSearchResult(count=len(rows), observations=rows)


def _serialize_observation(observation) -> ObservationResult:
    """Convert one SQLAlchemy observation to an MCP-safe result."""

    failure_types = [
        failure_type
        for failure_type, occurred in (
            ("TWF", observation.twf),
            ("HDF", observation.hdf),
            ("PWF", observation.pwf),
            ("OSF", observation.osf),
            ("RNF", observation.rnf),
        )
        if occurred
    ]
    return ObservationResult(
        found=True,
        udi=observation.udi,
        product_id=observation.product_id,
        product_type=observation.product_type,
        air_temperature=observation.air_temperature,
        process_temperature=observation.process_temperature,
        rotational_speed=observation.rotational_speed,
        torque=observation.torque,
        tool_wear=observation.tool_wear,
        machine_failure=observation.machine_failure,
        failure_types=failure_types,
    )


def main() -> None:
    """Run the MCP server over the standard-input/output transport."""

    server.run(transport="stdio")


if __name__ == "__main__":
    main()
