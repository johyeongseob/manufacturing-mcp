"""Load the AI4I 2020 CSV dataset into PostgreSQL."""

import argparse
import asyncio
import csv
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from manufacturing_mcp.config import get_settings
from manufacturing_mcp.database.models import Observation

CSV_COLUMNS = (
    "UDI",
    "Product ID",
    "Type",
    "Air temperature [K]",
    "Process temperature [K]",
    "Rotational speed [rpm]",
    "Torque [Nm]",
    "Tool wear [min]",
    "Machine failure",
    "TWF",
    "HDF",
    "PWF",
    "OSF",
    "RNF",
)


@dataclass(frozen=True)
class LoadResult:
    """Summary of one dataset load."""

    source_rows: int
    rows_before: int
    rows_after: int


def parse_binary(value: str, column: str) -> bool:
    """Convert a CSV binary value to bool while rejecting unexpected values."""

    if value not in {"0", "1"}:
        raise ValueError(f"{column} must be 0 or 1, received {value!r}")
    return value == "1"


def parse_row(row: Mapping[str, str]) -> dict[str, object]:
    """Convert one CSV row to values accepted by the Observation model."""

    return {
        "udi": int(row["UDI"]),
        "product_id": row["Product ID"],
        "product_type": row["Type"],
        "air_temperature": float(row["Air temperature [K]"]),
        "process_temperature": float(row["Process temperature [K]"]),
        "rotational_speed": int(row["Rotational speed [rpm]"]),
        "torque": float(row["Torque [Nm]"]),
        "tool_wear": int(row["Tool wear [min]"]),
        "machine_failure": parse_binary(row["Machine failure"], "Machine failure"),
        "twf": parse_binary(row["TWF"], "TWF"),
        "hdf": parse_binary(row["HDF"], "HDF"),
        "pwf": parse_binary(row["PWF"], "PWF"),
        "osf": parse_binary(row["OSF"], "OSF"),
        "rnf": parse_binary(row["RNF"], "RNF"),
    }


def read_csv(csv_path: Path) -> list[dict[str, object]]:
    """Read and validate every observation in the source CSV."""

    with csv_path.open(encoding="utf-8-sig", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        if tuple(reader.fieldnames or ()) != CSV_COLUMNS:
            raise ValueError("CSV columns do not match the expected AI4I 2020 schema")
        return [parse_row(row) for row in reader]


def batched(
    rows: Sequence[dict[str, object]],
    batch_size: int,
) -> Iterable[Sequence[dict[str, object]]]:
    """Yield fixed-size batches without copying the complete dataset."""

    if batch_size < 1:
        raise ValueError("batch_size must be at least 1")
    for start in range(0, len(rows), batch_size):
        yield rows[start : start + batch_size]


async def count_observations(engine: AsyncEngine) -> int:
    """Return the number of observation rows currently stored."""

    async with engine.connect() as connection:
        result = await connection.execute(select(func.count()).select_from(Observation))
        return result.scalar_one()


async def load_observations(
    engine: AsyncEngine,
    rows: Sequence[dict[str, object]],
    batch_size: int = 1_000,
) -> LoadResult:
    """Insert or update observations in one transaction."""

    rows_before = await count_observations(engine)
    async with engine.begin() as connection:
        for batch in batched(rows, batch_size):
            statement = insert(Observation).values(batch)
            update_columns = {
                column.name: getattr(statement.excluded, column.name)
                for column in Observation.__table__.columns
                if column.name != "udi"
            }
            statement = statement.on_conflict_do_update(
                index_elements=[Observation.udi],
                set_=update_columns,
            )
            await connection.execute(statement)

    rows_after = await count_observations(engine)
    return LoadResult(source_rows=len(rows), rows_before=rows_before, rows_after=rows_after)


def build_parser() -> argparse.ArgumentParser:
    """Build the dataset-loader command-line parser."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--csv",
        type=Path,
        default=Path("data/ai4i2020.csv"),
        help="Path to the AI4I 2020 CSV file",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=1_000,
        help="Rows written per PostgreSQL statement",
    )
    return parser


async def async_main(csv_path: Path, batch_size: int) -> LoadResult:
    """Load a CSV file using application database settings."""

    rows = read_csv(csv_path)
    engine = create_async_engine(get_settings().database_url)
    try:
        return await load_observations(engine, rows, batch_size)
    finally:
        await engine.dispose()


def main() -> None:
    """Run the dataset loader and print a non-sensitive summary."""

    args = build_parser().parse_args()
    result = asyncio.run(async_main(args.csv, args.batch_size))
    print(f"Source rows: {result.source_rows}")
    print(f"Database rows before load: {result.rows_before}")
    print(f"Database rows after load: {result.rows_after}")


if __name__ == "__main__":
    main()
