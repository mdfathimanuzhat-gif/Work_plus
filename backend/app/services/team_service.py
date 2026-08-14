"""Team management use cases."""

from __future__ import annotations

import uuid

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import APIError
from app.models.team import Team
from app.repositories import department as department_repository
from app.repositories import employee as employee_repository
from app.repositories import team as team_repository
from app.schemas.org import TeamCreate, TeamResponse, TeamUpdate
from app.services.authorization import (
    AuthenticatedUser,
    can_manage_teams,
    can_view_employee,
    can_view_team,
)
from app.services.employee_service import serialize_employee
from app.schemas.employee import EmployeeResponse


def serialize_team(team: Team) -> TeamResponse:
    lead = team.team_lead
    return TeamResponse(
        id=team.id,
        organization_id=team.organization_id,
        name=team.name,
        description=team.description,
        department_id=team.department_id,
        department_name=team.department.name if team.department else None,
        team_lead_id=team.team_lead_id,
        team_lead_name=f"{lead.first_name} {lead.last_name}" if lead else None,
        is_active=team.is_active,
        created_at=team.created_at,
        updated_at=team.updated_at,
    )


def list_visible_teams(session: Session, user: AuthenticatedUser) -> list[Team]:
    teams = team_repository.list_teams(session, user.organization_id)
    return [team for team in teams if can_view_team(user, team.id)]


def get_visible_team(session: Session, user: AuthenticatedUser, team_id: uuid.UUID) -> Team:
    team = team_repository.get_team_by_id(session, team_id)
    if team is None or team.organization_id != user.organization_id:
        raise APIError(404, "not_found", "Team not found")
    if not can_view_team(user, team.id):
        raise APIError(403, "forbidden", "You do not have access to this team")
    return team


def list_team_members(session: Session, user: AuthenticatedUser, team_id: uuid.UUID) -> list[EmployeeResponse]:
    team = get_visible_team(session, user, team_id)
    members = employee_repository.list_employees_on_team(session, team.id)
    return [serialize_employee(member) for member in members if can_view_employee(user, member)]


def _validate_team_department(session: Session, user: AuthenticatedUser, department_id: uuid.UUID):
    department = department_repository.get_department_by_id(session, department_id)
    if department is None or department.organization_id != user.organization_id:
        raise APIError(400, "invalid_department", "Department is invalid for this organization")
    return department


def _validate_team_lead(session: Session, user: AuthenticatedUser, team_lead_id: uuid.UUID):
    lead = employee_repository.get_employee_by_id(session, team_lead_id)
    if lead is None or lead.organization_id != user.organization_id:
        raise APIError(400, "invalid_team_lead", "Team lead must belong to the same organization")
    if not lead.is_active:
        raise APIError(400, "invalid_team_lead", "Team lead is inactive")
    role_names = {assignment.role.name for assignment in lead.employee_roles}
    if not role_names.intersection({"TEAM_LEAD", "ADMIN"}):
        raise APIError(400, "invalid_team_lead", "Team lead must have the TEAM_LEAD role")
    return lead


def create_team(session: Session, user: AuthenticatedUser, payload: TeamCreate) -> Team:
    if not can_manage_teams(user):
        raise APIError(403, "forbidden", "You do not have access to this resource")
    if team_repository.get_team_by_name(session, user.organization_id, payload.name.strip()):
        raise APIError(409, "duplicate_team", "Team name already exists")
    if payload.department_id is not None:
        _validate_team_department(session, user, payload.department_id)
    if payload.team_lead_id is not None:
        _validate_team_lead(session, user, payload.team_lead_id)
    team = Team(
        organization_id=user.organization_id,
        name=payload.name.strip(),
        description=payload.description,
        department_id=payload.department_id,
        team_lead_id=payload.team_lead_id,
        is_active=True,
    )
    session.add(team)
    try:
        session.flush()
    except IntegrityError as exc:
        raise APIError(409, "duplicate_team", "Team name already exists") from exc
    return team_repository.get_team_by_id(session, team.id) or team


def update_team(session: Session, user: AuthenticatedUser, team_id: uuid.UUID, payload: TeamUpdate) -> Team:
    if not can_manage_teams(user):
        raise APIError(403, "forbidden", "You do not have access to this resource")
    team = team_repository.get_team_by_id(session, team_id)
    if team is None or team.organization_id != user.organization_id:
        raise APIError(404, "not_found", "Team not found")
    updates = payload.model_dump(exclude_unset=True)
    if "department_id" in updates and updates["department_id"] is not None:
        _validate_team_department(session, user, updates["department_id"])
    if "team_lead_id" in updates and updates["team_lead_id"] is not None:
        _validate_team_lead(session, user, updates["team_lead_id"])
    if "name" in updates and updates["name"]:
        existing = team_repository.get_team_by_name(session, user.organization_id, updates["name"].strip())
        if existing is not None and existing.id != team.id:
            raise APIError(409, "duplicate_team", "Team name already exists")
        updates["name"] = updates["name"].strip()
    for field, value in updates.items():
        setattr(team, field, value)
    session.flush()
    return team_repository.get_team_by_id(session, team.id) or team
