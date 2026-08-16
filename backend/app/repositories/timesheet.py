"""Timesheet data-access helpers."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import Select, select
from sqlalchemy.orm import Session, selectinload

from app.models.employee import Employee
from app.models.enums import TimesheetApprovalStatus, TimesheetStatus
from app.models.timesheet import Timesheet, TimesheetApproval


def _with_approvals(statement: Select[tuple[Timesheet]]) -> Select[tuple[Timesheet]]:
    return statement.options(selectinload(Timesheet.approvals), selectinload(Timesheet.employee))


def get_timesheet_by_id(session: Session, timesheet_id: uuid.UUID) -> Timesheet | None:
    return session.scalar(
        _with_approvals(select(Timesheet).where(Timesheet.id == timesheet_id))
    )


def create_timesheet(
    session: Session,
    *,
    employee_id: uuid.UUID,
    work_date: date,
    project: str,
    task: str,
    description: str | None,
    hours,
) -> Timesheet:
    row = Timesheet(
        employee_id=employee_id,
        date=work_date,
        project=project.strip(),
        task=task.strip(),
        description=description.strip() if description else None,
        hours=hours,
        status=TimesheetStatus.DRAFT,
    )
    session.add(row)
    session.flush()
    return get_timesheet_by_id(session, row.id) or row


def list_for_employee(
    session: Session,
    employee_id: uuid.UUID,
    *,
    date_from: date | None = None,
    date_to: date | None = None,
) -> list[Timesheet]:
    statement = _with_approvals(select(Timesheet).where(Timesheet.employee_id == employee_id))
    if date_from is not None:
        statement = statement.where(Timesheet.date >= date_from)
    if date_to is not None:
        statement = statement.where(Timesheet.date <= date_to)
    statement = statement.order_by(Timesheet.date.desc(), Timesheet.created_at.desc())
    return list(session.scalars(statement).unique())


def list_for_direct_reports(
    session: Session,
    manager_id: uuid.UUID,
    *,
    statuses: list[TimesheetStatus] | None = None,
) -> list[Timesheet]:
    statement = (
        _with_approvals(select(Timesheet))
        .join(Employee, Employee.id == Timesheet.employee_id)
        .where(Employee.manager_id == manager_id)
    )
    if statuses:
        statement = statement.where(Timesheet.status.in_(statuses))
    statement = statement.order_by(Timesheet.date.desc(), Timesheet.created_at.desc())
    return list(session.scalars(statement).unique())


def list_for_organization(
    session: Session,
    organization_id: uuid.UUID,
    *,
    statuses: list[TimesheetStatus] | None = None,
) -> list[Timesheet]:
    statement = (
        _with_approvals(select(Timesheet))
        .join(Employee, Employee.id == Timesheet.employee_id)
        .where(Employee.organization_id == organization_id)
    )
    if statuses:
        statement = statement.where(Timesheet.status.in_(statuses))
    statement = statement.order_by(Timesheet.date.desc(), Timesheet.created_at.desc())
    return list(session.scalars(statement).unique())


def get_approval_for_reviewer(
    session: Session,
    timesheet_id: uuid.UUID,
    reviewer_id: uuid.UUID,
) -> TimesheetApproval | None:
    return session.scalar(
        select(TimesheetApproval).where(
            TimesheetApproval.timesheet_id == timesheet_id,
            TimesheetApproval.reviewer_id == reviewer_id,
        )
    )


def upsert_approval(
    session: Session,
    *,
    timesheet: Timesheet,
    reviewer_id: uuid.UUID,
    status: TimesheetApprovalStatus,
    comments: str | None,
    reviewed_at: datetime,
) -> TimesheetApproval:
    existing = get_approval_for_reviewer(session, timesheet.id, reviewer_id)
    if existing is None:
        existing = TimesheetApproval(
            timesheet_id=timesheet.id,
            reviewer_id=reviewer_id,
        )
        session.add(existing)
    existing.status = status
    existing.comments = comments
    existing.reviewed_at = reviewed_at
    session.flush()
    return existing
