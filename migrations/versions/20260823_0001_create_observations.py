"""Create the observations table.

Revision ID: 20260823_0001
Revises: None
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260823_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create the observations table and query indexes."""

    op.create_table(
        "observations",
        sa.Column("udi", sa.Integer(), autoincrement=False, nullable=False),
        sa.Column("product_id", sa.String(length=10), nullable=False),
        sa.Column("product_type", sa.String(length=1), nullable=False),
        sa.Column("air_temperature", sa.Float(), nullable=False),
        sa.Column("process_temperature", sa.Float(), nullable=False),
        sa.Column("rotational_speed", sa.Integer(), nullable=False),
        sa.Column("torque", sa.Float(), nullable=False),
        sa.Column("tool_wear", sa.Integer(), nullable=False),
        sa.Column("machine_failure", sa.Boolean(), nullable=False),
        sa.Column("twf", sa.Boolean(), nullable=False),
        sa.Column("hdf", sa.Boolean(), nullable=False),
        sa.Column("pwf", sa.Boolean(), nullable=False),
        sa.Column("osf", sa.Boolean(), nullable=False),
        sa.Column("rnf", sa.Boolean(), nullable=False),
        sa.CheckConstraint(
            "air_temperature > 0",
            name=op.f("ck_observations_air_temperature_positive"),
        ),
        sa.CheckConstraint(
            "process_temperature > 0",
            name=op.f("ck_observations_process_temperature_positive"),
        ),
        sa.CheckConstraint(
            "product_type IN ('L', 'M', 'H')",
            name=op.f("ck_observations_product_type"),
        ),
        sa.CheckConstraint(
            "rotational_speed > 0",
            name=op.f("ck_observations_rotational_speed_positive"),
        ),
        sa.CheckConstraint("tool_wear >= 0", name=op.f("ck_observations_tool_wear_nonnegative")),
        sa.CheckConstraint("torque >= 0", name=op.f("ck_observations_torque_nonnegative")),
        sa.PrimaryKeyConstraint("udi", name=op.f("pk_observations")),
        sa.UniqueConstraint("product_id", name=op.f("uq_observations_product_id")),
    )
    op.create_index("ix_observations_machine_failure", "observations", ["machine_failure"])
    op.create_index("ix_observations_product_type", "observations", ["product_type"])


def downgrade() -> None:
    """Remove the observations table."""

    op.drop_index("ix_observations_product_type", table_name="observations")
    op.drop_index("ix_observations_machine_failure", table_name="observations")
    op.drop_table("observations")
