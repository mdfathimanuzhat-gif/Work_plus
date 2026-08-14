"""Add attendance session rows and derived duration fields.

Revision ID: c7e91b4a2d10
Revises: 9c4e2a71f0b3
Create Date: 2026-08-14 10:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "c7e91b4a2d10"
down_revision: Union[str, None] = "9c4e2a71f0b3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE attendance_status ADD VALUE IF NOT EXISTS 'PARTIAL'")
    attendance_session_status = postgresql.ENUM(
        "OPEN",
        "CLOSED",
        "CONTINUED",
        name="attendance_session_status",
        create_type=True,
    )
    attendance_session_status.create(op.get_bind(), checkfirst=True)

    op.add_column("attendance", sa.Column("total_sleep_seconds", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("attendance", sa.Column("total_session_seconds", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("attendance", sa.Column("session_count", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("attendance", sa.Column("is_complete", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("attendance", sa.Column("calculated_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("attendance", sa.Column("anomalies", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.create_check_constraint("total_sleep_seconds_non_negative", "attendance", "total_sleep_seconds >= 0")
    op.create_check_constraint("total_session_seconds_non_negative", "attendance", "total_session_seconds >= 0")
    op.create_check_constraint("session_count_non_negative", "attendance", "session_count >= 0")

    op.create_table(
        "attendance_sessions",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("attendance_id", sa.Uuid(), nullable=False),
        sa.Column("employee_id", sa.Uuid(), nullable=False),
        sa.Column("device_id", sa.Uuid(), nullable=True),
        sa.Column("session_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("session_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("session_duration_seconds", sa.Integer(), nullable=False),
        sa.Column("locked_seconds", sa.Integer(), nullable=False),
        sa.Column("idle_seconds", sa.Integer(), nullable=False),
        sa.Column("sleep_seconds", sa.Integer(), nullable=False),
        sa.Column("active_seconds", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            postgresql.ENUM("OPEN", "CLOSED", "CONTINUED", name="attendance_session_status", create_type=False),
            nullable=False,
        ),
        sa.Column("ended_reason", sa.String(length=50), nullable=True),
        sa.CheckConstraint("session_duration_seconds >= 0", name="session_duration_seconds_non_negative"),
        sa.CheckConstraint("locked_seconds >= 0", name="session_locked_seconds_non_negative"),
        sa.CheckConstraint("idle_seconds >= 0", name="session_idle_seconds_non_negative"),
        sa.CheckConstraint("sleep_seconds >= 0", name="session_sleep_seconds_non_negative"),
        sa.CheckConstraint("active_seconds >= 0", name="session_active_seconds_non_negative"),
        sa.ForeignKeyConstraint(["attendance_id"], ["attendance.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["employee_id"], ["employees.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["device_id"], ["devices.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_attendance_sessions_attendance_id", "attendance_sessions", ["attendance_id"])
    op.create_index("ix_attendance_sessions_employee_id", "attendance_sessions", ["employee_id"])
    op.create_index("ix_attendance_sessions_device_id", "attendance_sessions", ["device_id"])
    op.create_index(
        "ix_attendance_sessions_employee_id_session_start",
        "attendance_sessions",
        ["employee_id", "session_start"],
    )


def downgrade() -> None:
    op.drop_index("ix_attendance_sessions_employee_id_session_start", table_name="attendance_sessions")
    op.drop_index("ix_attendance_sessions_device_id", table_name="attendance_sessions")
    op.drop_index("ix_attendance_sessions_employee_id", table_name="attendance_sessions")
    op.drop_index("ix_attendance_sessions_attendance_id", table_name="attendance_sessions")
    op.drop_table("attendance_sessions")
    op.execute("DROP TYPE IF EXISTS attendance_session_status")
    op.drop_constraint("session_count_non_negative", "attendance", type_="check")
    op.drop_constraint("total_session_seconds_non_negative", "attendance", type_="check")
    op.drop_constraint("total_sleep_seconds_non_negative", "attendance", type_="check")
    op.drop_column("attendance", "anomalies")
    op.drop_column("attendance", "calculated_at")
    op.drop_column("attendance", "is_complete")
    op.drop_column("attendance", "session_count")
    op.drop_column("attendance", "total_session_seconds")
    op.drop_column("attendance", "total_sleep_seconds")
