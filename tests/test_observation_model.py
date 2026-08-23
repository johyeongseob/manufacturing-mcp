"""Tests for the manufacturing observation database model."""

from sqlalchemy import Boolean, Float, Integer, String

from manufacturing_mcp.database.models import Observation


def test_observation_table_matches_dataset_schema() -> None:
    table = Observation.__table__

    assert table.name == "observations"
    assert list(table.columns.keys()) == [
        "udi",
        "product_id",
        "product_type",
        "air_temperature",
        "process_temperature",
        "rotational_speed",
        "torque",
        "tool_wear",
        "machine_failure",
        "twf",
        "hdf",
        "pwf",
        "osf",
        "rnf",
    ]
    assert table.primary_key.columns.keys() == ["udi"]
    assert table.columns.udi.autoincrement is False
    assert all(column.nullable is False for column in table.columns)


def test_observation_columns_use_expected_types() -> None:
    columns = Observation.__table__.columns

    assert isinstance(columns.udi.type, Integer)
    assert isinstance(columns.product_id.type, String)
    assert isinstance(columns.product_type.type, String)
    assert isinstance(columns.air_temperature.type, Float)
    assert isinstance(columns.process_temperature.type, Float)
    assert isinstance(columns.rotational_speed.type, Integer)
    assert isinstance(columns.torque.type, Float)
    assert isinstance(columns.tool_wear.type, Integer)
    assert all(
        isinstance(columns[name].type, Boolean)
        for name in ("machine_failure", "twf", "hdf", "pwf", "osf", "rnf")
    )
