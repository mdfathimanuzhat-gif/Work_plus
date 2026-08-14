"""PostgreSQL-backed enumerations for WorkPulse domain values."""

from enum import Enum

from sqlalchemy import Enum as SAEnum


class EmploymentStatus(str, Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    ON_LEAVE = "ON_LEAVE"
    TERMINATED = "TERMINATED"


class AttendanceStatus(str, Enum):
    PRESENT = "PRESENT"
    ABSENT = "ABSENT"
    HALF_DAY = "HALF_DAY"
    ON_LEAVE = "ON_LEAVE"
    HOLIDAY = "HOLIDAY"
    INCOMPLETE = "INCOMPLETE"


class AttendanceEventType(str, Enum):
    LOGIN = "LOGIN"
    LOGOUT = "LOGOUT"
    LOCK = "LOCK"
    UNLOCK = "UNLOCK"
    SHUTDOWN = "SHUTDOWN"
    RESTART = "RESTART"
    SLEEP = "SLEEP"
    WAKE = "WAKE"
    IDLE_START = "IDLE_START"
    IDLE_END = "IDLE_END"


class TimesheetStatus(str, Enum):
    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class TimesheetApprovalStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class LocationType(str, Enum):
    GPS = "GPS"
    IP = "IP"
    MANUAL = "MANUAL"
    UNKNOWN = "UNKNOWN"


class NotificationType(str, Enum):
    SYSTEM = "SYSTEM"
    ATTENDANCE = "ATTENDANCE"
    TIMESHEET = "TIMESHEET"
    APPROVAL = "APPROVAL"


def pg_enum(enum_cls: type[Enum], name: str) -> SAEnum:
    """Native PostgreSQL ENUM using the member values, not Python names."""
    return SAEnum(
        enum_cls,
        name=name,
        native_enum=True,
        create_constraint=False,
        values_callable=lambda members: [member.value for member in members],
    )
