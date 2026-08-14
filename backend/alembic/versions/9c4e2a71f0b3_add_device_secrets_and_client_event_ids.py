"""Add device secrets and unique client event ids for agent sync.

Revision ID: 9c4e2a71f0b3
Revises: 1b031dbbcee4
Create Date: 2026-08-14 09:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "9c4e2a71f0b3"
down_revision: Union[str, None] = "1b031dbbcee4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("devices", sa.Column("secret_hash", sa.String(length=64), nullable=True))
    op.create_unique_constraint("uq_devices_secret_hash", "devices", ["secret_hash"])
    op.add_column("attendance_events", sa.Column("client_event_id", sa.Uuid(), nullable=True))
    op.execute("UPDATE attendance_events SET client_event_id = id WHERE client_event_id IS NULL")
    op.alter_column("attendance_events", "client_event_id", nullable=False)
    op.create_unique_constraint("uq_attendance_events_client_event_id", "attendance_events", ["client_event_id"])
    op.create_index(
        "ix_attendance_events_employee_id_event_time",
        "attendance_events",
        ["employee_id", "event_time"],
        unique=False,
    )
    op.create_index(
        "ix_attendance_events_device_id_event_time",
        "attendance_events",
        ["device_id", "event_time"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_attendance_events_device_id_event_time", table_name="attendance_events")
    op.drop_index("ix_attendance_events_employee_id_event_time", table_name="attendance_events")
    op.drop_constraint("uq_attendance_events_client_event_id", "attendance_events", type_="unique")
    op.drop_column("attendance_events", "client_event_id")
    op.drop_constraint("uq_devices_secret_hash", "devices", type_="unique")
    op.drop_column("devices", "secret_hash")
