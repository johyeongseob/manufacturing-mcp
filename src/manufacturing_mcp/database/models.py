"""SQLAlchemy models for manufacturing data."""

from sqlalchemy import Boolean, CheckConstraint, Float, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from manufacturing_mcp.database.base import Base


class Observation(Base):
    """One operating-condition observation from the AI4I 2020 dataset."""

    __tablename__ = "observations"
    __table_args__ = (
        CheckConstraint("product_type IN ('L', 'M', 'H')", name="product_type"),
        CheckConstraint("air_temperature > 0", name="air_temperature_positive"),
        CheckConstraint("process_temperature > 0", name="process_temperature_positive"),
        CheckConstraint("rotational_speed > 0", name="rotational_speed_positive"),
        CheckConstraint("torque >= 0", name="torque_nonnegative"),
        CheckConstraint("tool_wear >= 0", name="tool_wear_nonnegative"),
        Index("ix_observations_product_type", "product_type"),
        Index("ix_observations_machine_failure", "machine_failure"),
    )

    udi: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    product_id: Mapped[str] = mapped_column(String(10), unique=True)
    product_type: Mapped[str] = mapped_column(String(1))
    air_temperature: Mapped[float] = mapped_column(Float)
    process_temperature: Mapped[float] = mapped_column(Float)
    rotational_speed: Mapped[int] = mapped_column(Integer)
    torque: Mapped[float] = mapped_column(Float)
    tool_wear: Mapped[int] = mapped_column(Integer)
    machine_failure: Mapped[bool] = mapped_column(Boolean)
    twf: Mapped[bool] = mapped_column(Boolean)
    hdf: Mapped[bool] = mapped_column(Boolean)
    pwf: Mapped[bool] = mapped_column(Boolean)
    osf: Mapped[bool] = mapped_column(Boolean)
    rnf: Mapped[bool] = mapped_column(Boolean)
