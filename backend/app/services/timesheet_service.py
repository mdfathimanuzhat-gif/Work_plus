"""Timesheet create, submit, and review workflows."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import APIError
from app.models.enums import TimesheetApprovalStatus, TimesheetStatus
from app.models.timesheet import Timesheet
from app.repositories import timesheet as timesheet_repository
from app.schemas.timesheet import (
    ApprovalDecision,
    TimesheetApprovalOut,
    TimesheetCreate,
    TimesheetDetailOut,
    TimesheetOut,
)
from app.services.authorization import AuthenticatedUser, has_permission, has_role, require_role


def serialize_timesheet(row: Timesheet) -> TimesheetOut:
    return TimesheetOut.model_validate(row)


def serialize_timesheet_detail(row: Timesheet) -> TimesheetDetailOut:
    approvals = sorted(row.approvals, key=lambda item: item.created_at)
    return TimesheetDetailOut(
        **serialize_timesheet(row).model_dump(),
        approvals=[TimesheetApprovalOut.model_validate(item) for item in approvals],
    )


def _ensure_own_permission(user: AuthenticatedUser) -> None:
    if not has_permission(user, "timesheet.manage_own") and not has_role(user, "EMPLOYEE", "TEAM_LEAD", "HR", "ADMIN"):
        raise APIError(403, "forbidden", "You do not have access to this resource")


def create_own_entry(session: Session, user: AuthenticatedUser, payload: TimesheetCreate) -> Timesheet:
    _ensure_own_permission(user)
    try:
        row = timesheet_repository.create_timesheet(
            session,
            employee_id=user.employee_id,
            work_date=payload.date,
            project=payload.project,
            task=payload.task,
            description=payload.description,
            hours=payload.hours,
        )
        session.flush()
    except IntegrityError as exc:
        session.rollback()
        raise APIError(
            409,
            "conflict",
            "A timesheet entry already exists for this date, project, and task",
        ) from exc
    loaded = timesheet_repository.get_timesheet_by_id(session, row.id)
    return loaded or row


def list_own_entries(
    session: Session,
    user: AuthenticatedUser,
    date_from: date | None,
    date_to: date | None,
) -> list[Timesheet]:
    _ensure_own_permission(user)
    return timesheet_repository.list_for_employee(
        session,
        user.employee_id,
        date_from=date_from,
        date_to=date_to,
    )


def submit_own_entry(session: Session, user: AuthenticatedUser, timesheet_id: uuid.UUID) -> Timesheet:
    _ensure_own_permission(user)
    row = timesheet_repository.get_timesheet_by_id(session, timesheet_id)
    if row is None or row.employee.organization_id != user.organization_id:
        raise APIError(404, "not_found", "Timesheet entry not found")
    if row.employee_id != user.employee_id:
        raise APIError(403, "forbidden", "You can only submit your own timesheet entries")
    if row.status != TimesheetStatus.DRAFT:
        raise APIError(409, "conflict", "Only draft timesheet entries can be submitted")
    row.status = TimesheetStatus.SUBMITTED
    row.submitted_at = datetime.now(timezone.utc)
    session.flush()
    return timesheet_repository.get_timesheet_by_id(session, row.id) or row


def list_team_queue(session: Session, user: AuthenticatedUser) -> list[Timesheet]:
    require_role(user, "TEAM_LEAD", "HR", "ADMIN")
    submitted = [TimesheetStatus.SUBMITTED]
    if has_role(user, "HR", "ADMIN") or has_permission(user, "timesheet.view_organization"):
        return timesheet_repository.list_for_organization(
            session,
            user.organization_id,
            statuses=submitted,
        )
    return timesheet_repository.list_for_direct_reports(
        session,
        user.employee_id,
        statuses=submitted,
    )


def _can_view_entry(user: AuthenticatedUser, row: Timesheet) -> bool:
    if row.employee.organization_id != user.organization_id:
        return False
    if row.employee_id == user.employee_id:
        return True
    if has_role(user, "HR", "ADMIN") or has_permission(user, "timesheet.view_organization"):
        return True
    if has_role(user, "TEAM_LEAD") or has_permission(user, "timesheet.review_team"):
        return row.employee.manager_id == user.employee_id
    return False


def get_visible_entry(session: Session, user: AuthenticatedUser, timesheet_id: uuid.UUID) -> Timesheet:
    row = timesheet_repository.get_timesheet_by_id(session, timesheet_id)
    if row is None or row.employee.organization_id != user.organization_id:
        raise APIError(404, "not_found", "Timesheet entry not found")
    if not _can_view_entry(user, row):
        raise APIError(403, "forbidden", "You do not have access to this timesheet entry")
    return row


def _can_review_entry(user: AuthenticatedUser, row: Timesheet) -> bool:
    if row.employee_id == user.employee_id:
        return False
    if row.employee.organization_id != user.organization_id:
        return False
    if has_role(user, "HR", "ADMIN") or has_permission(user, "timesheet.view_organization"):
        return True
    if has_role(user, "TEAM_LEAD") or has_permission(user, "timesheet.review_team"):
        return row.employee.manager_id == user.employee_id
    return False


def review_entry(
    session: Session,
    user: AuthenticatedUser,
    timesheet_id: uuid.UUID,
    decision: ApprovalDecision,
) -> Timesheet:
    require_role(user, "TEAM_LEAD", "HR", "ADMIN")
    row = timesheet_repository.get_timesheet_by_id(session, timesheet_id)
    if row is None or row.employee.organization_id != user.organization_id:
        raise APIError(404, "not_found", "Timesheet entry not found")
    if not _can_review_entry(user, row):
        raise APIError(403, "forbidden", "You cannot review this timesheet entry")
    if row.status != TimesheetStatus.SUBMITTED:
        raise APIError(409, "conflict", "Only submitted timesheet entries can be reviewed")

    reviewed_at = datetime.now(timezone.utc)
    timesheet_repository.upsert_approval(
        session,
        timesheet=row,
        reviewer_id=user.employee_id,
        status=decision.status,
        comments=decision.comments,
        reviewed_at=reviewed_at,
    )
    if decision.status == TimesheetApprovalStatus.APPROVED:
        row.status = TimesheetStatus.APPROVED
    else:
        row.status = TimesheetStatus.REJECTED
    session.flush()
    loaded = timesheet_repository.get_timesheet_by_id(session, row.id)
    return loaded or row
