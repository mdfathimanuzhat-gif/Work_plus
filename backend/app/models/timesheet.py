"""Timesheet and approval persistence models."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.enums import TimesheetApprovalStatus, TimesheetStatus, pg_enum
from app.models.mixins import CreatedAtMixin, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.employee import Employee


class Timesheet(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "timesheets"
    __table_args__ = (
        UniqueConstraint(
            "employee_id",
            "date",
            "project",
            "task",
            name="uq_timesheets_employee_id_date_project_task",
        ),
        CheckConstraint("hours >= 0", name="hours_non_negative"),
        Index("ix_timesheets_date", "date"),
        Index("ix_timesheets_status", "status"),
    )

    employee_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("employees.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    date: Mapped[date] = mapped_column(Date, nullable=False)
    project: Mapped[str] = mapped_column(String(255), nullable=False)
    task: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    hours: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False)
    status: Mapped[TimesheetStatus] = mapped_column(
        pg_enum(TimesheetStatus, "timesheet_status"),
        nullable=False,
        default=TimesheetStatus.DRAFT,
    )
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    employee: Mapped[Employee] = relationship(back_populates="timesheets")
    approvals: Mapped[list[TimesheetApproval]] = relationship(
        back_populates="timesheet",
        cascade="all, delete-orphan",
    )


class TimesheetApproval(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "timesheet_approvals"

    timesheet_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("timesheets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    reviewer_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("employees.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    status: Mapped[TimesheetApprovalStatus] = mapped_column(
        pg_enum(TimesheetApprovalStatus, "timesheet_approval_status"),
        nullable=False,
        default=TimesheetApprovalStatus.PENDING,
    )
    comments: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    timesheet: Mapped[Timesheet] = relationship(back_populates="approvals")
    reviewer: Mapped[Employee] = relationship(
        back_populates="timesheet_reviews",
        foreign_keys="TimesheetApproval.reviewer_id",
    )
