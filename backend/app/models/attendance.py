"""Attendance summary, session, and event persistence models."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.enums import AttendanceEventType, AttendanceSessionStatus, AttendanceStatus, pg_enum
from app.models.mixins import CreatedAtMixin, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.device import Device
    from app.models.employee import Employee


class Attendance(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "attendance"
    __table_args__ = (
        UniqueConstraint(
            "employee_id",
            "attendance_date",
            name="uq_attendance_employee_id_attendance_date",
        ),
        CheckConstraint("total_work_seconds >= 0", name="total_work_seconds_non_negative"),
        CheckConstraint("total_idle_seconds >= 0", name="total_idle_seconds_non_negative"),
        CheckConstraint("total_locked_seconds >= 0", name="total_locked_seconds_non_negative"),
        CheckConstraint("total_sleep_seconds >= 0", name="total_sleep_seconds_non_negative"),
        CheckConstraint("total_session_seconds >= 0", name="total_session_seconds_non_negative"),
        CheckConstraint("session_count >= 0", name="session_count_non_negative"),
        Index("ix_attendance_attendance_date", "attendance_date"),
    )

    employee_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("employees.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    attendance_date: Mapped[date] = mapped_column(Date, nullable=False)
    check_in_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    check_out_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    total_work_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_idle_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_locked_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_sleep_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_session_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    session_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_complete: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    calculated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[AttendanceStatus] = mapped_column(
        pg_enum(AttendanceStatus, "attendance_status"),
        nullable=False,
        default=AttendanceStatus.INCOMPLETE,
    )
    anomalies: Mapped[list | None] = mapped_column(JSONB, nullable=True)

    employee: Mapped[Employee] = relationship(back_populates="attendance_records")
    events: Mapped[list[AttendanceEvent]] = relationship(back_populates="attendance")
    sessions: Mapped[list[AttendanceSession]] = relationship(
        back_populates="attendance",
        cascade="all, delete-orphan",
    )


class AttendanceSession(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "attendance_sessions"
    __table_args__ = (
        CheckConstraint("session_duration_seconds >= 0", name="session_duration_seconds_non_negative"),
        CheckConstraint("locked_seconds >= 0", name="session_locked_seconds_non_negative"),
        CheckConstraint("idle_seconds >= 0", name="session_idle_seconds_non_negative"),
        CheckConstraint("sleep_seconds >= 0", name="session_sleep_seconds_non_negative"),
        CheckConstraint("active_seconds >= 0", name="session_active_seconds_non_negative"),
        Index("ix_attendance_sessions_employee_id_session_start", "employee_id", "session_start"),
    )

    attendance_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("attendance.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    employee_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("employees.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    device_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("devices.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    session_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    session_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    session_duration_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    locked_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    idle_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    sleep_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    active_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[AttendanceSessionStatus] = mapped_column(
        pg_enum(AttendanceSessionStatus, "attendance_session_status"),
        nullable=False,
        default=AttendanceSessionStatus.OPEN,
    )
    ended_reason: Mapped[str | None] = mapped_column(String(50), nullable=True)

    attendance: Mapped[Attendance] = relationship(back_populates="sessions")
    employee: Mapped[Employee] = relationship(back_populates="attendance_sessions")
    device: Mapped[Device | None] = relationship()


class AttendanceEvent(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "attendance_events"
    __table_args__ = (
        UniqueConstraint("client_event_id", name="uq_attendance_events_client_event_id"),
        Index("ix_attendance_events_event_time", "event_time"),
        Index("ix_attendance_events_employee_id_event_time", "employee_id", "event_time"),
        Index("ix_attendance_events_device_id_event_time", "device_id", "event_time"),
    )

    employee_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("employees.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    device_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("devices.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    attendance_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("attendance.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    client_event_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    event_type: Mapped[AttendanceEventType] = mapped_column(
        pg_enum(AttendanceEventType, "attendance_event_type"),
        nullable=False,
    )
    event_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    event_metadata: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)

    employee: Mapped[Employee] = relationship(back_populates="attendance_events")
    device: Mapped[Device | None] = relationship(back_populates="attendance_events")
    attendance: Mapped[Attendance | None] = relationship(back_populates="events")
