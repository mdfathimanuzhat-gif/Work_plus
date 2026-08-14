"""Employee persistence model."""

from __future__ import annotations

import uuid
from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Date, ForeignKey, Index, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.enums import EmploymentStatus, pg_enum
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.attendance import Attendance, AttendanceEvent
    from app.models.audit_log import AuditLog
    from app.models.department import Department
    from app.models.device import Device
    from app.models.location import Location
    from app.models.notification import Notification
    from app.models.organization import Organization
    from app.models.rbac import EmployeeRole
    from app.models.team import Team
    from app.models.timesheet import Timesheet, TimesheetApproval
    from app.models.user_account import UserAccount


class Employee(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "employees"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "employee_code",
            name="uq_employees_organization_id_employee_code",
        ),
        UniqueConstraint(
            "organization_id",
            "email",
            name="uq_employees_organization_id_email",
        ),
        Index("ix_employees_employee_code", "employee_code"),
        Index("ix_employees_email", "email"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("organizations.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    employee_code: Mapped[str] = mapped_column(String(50), nullable=False)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    department_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("departments.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    team_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("teams.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    manager_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("employees.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    joining_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    employment_status: Mapped[EmploymentStatus] = mapped_column(
        pg_enum(EmploymentStatus, "employment_status"),
        nullable=False,
        default=EmploymentStatus.ACTIVE,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    organization: Mapped[Organization] = relationship(back_populates="employees")
    department: Mapped[Department | None] = relationship(back_populates="employees")
    team: Mapped[Team | None] = relationship(
        back_populates="employees",
        foreign_keys="Employee.team_id",
    )
    led_teams: Mapped[list[Team]] = relationship(
        back_populates="team_lead",
        foreign_keys="Team.team_lead_id",
    )
    manager: Mapped[Employee | None] = relationship(
        back_populates="direct_reports",
        remote_side="Employee.id",
        foreign_keys="Employee.manager_id",
    )
    direct_reports: Mapped[list[Employee]] = relationship(
        back_populates="manager",
        foreign_keys="Employee.manager_id",
    )
    employee_roles: Mapped[list[EmployeeRole]] = relationship(
        back_populates="employee",
        cascade="all, delete-orphan",
    )
    account: Mapped[UserAccount | None] = relationship(
        back_populates="employee",
        uselist=False,
        cascade="all, delete-orphan",
        single_parent=True,
    )
    devices: Mapped[list[Device]] = relationship(
        back_populates="employee",
        cascade="all, delete-orphan",
    )
    attendance_records: Mapped[list[Attendance]] = relationship(
        back_populates="employee",
        cascade="all, delete-orphan",
    )
    attendance_events: Mapped[list[AttendanceEvent]] = relationship(
        back_populates="employee",
        cascade="all, delete-orphan",
    )
    timesheets: Mapped[list[Timesheet]] = relationship(
        back_populates="employee",
        cascade="all, delete-orphan",
    )
    timesheet_reviews: Mapped[list[TimesheetApproval]] = relationship(
        back_populates="reviewer",
        foreign_keys="TimesheetApproval.reviewer_id",
    )
    locations: Mapped[list[Location]] = relationship(
        back_populates="employee",
        cascade="all, delete-orphan",
    )
    notifications: Mapped[list[Notification]] = relationship(
        back_populates="employee",
        cascade="all, delete-orphan",
    )
    audit_logs: Mapped[list[AuditLog]] = relationship(
        back_populates="user",
        foreign_keys="AuditLog.user_id",
    )
