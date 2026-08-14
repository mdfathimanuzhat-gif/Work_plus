"""Team routes."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser
from app.database.session import get_db
from app.schemas.employee import EmployeeResponse
from app.schemas.org import TeamCreate, TeamResponse, TeamUpdate
from app.services import team_service

router = APIRouter(prefix="/teams", tags=["teams"])


@router.get("", response_model=list[TeamResponse])
def list_teams(
    user: CurrentUser,
    session: Annotated[Session, Depends(get_db)],
) -> list[TeamResponse]:
    teams = team_service.list_visible_teams(session, user)
    return [team_service.serialize_team(team) for team in teams]


@router.post("", response_model=TeamResponse, status_code=201)
def create_team(
    body: TeamCreate,
    user: CurrentUser,
    session: Annotated[Session, Depends(get_db)],
) -> TeamResponse:
    team = team_service.create_team(session, user, body)
    session.commit()
    return team_service.serialize_team(team)


@router.get("/{team_id}", response_model=TeamResponse)
def get_team(
    team_id: uuid.UUID,
    user: CurrentUser,
    session: Annotated[Session, Depends(get_db)],
) -> TeamResponse:
    team = team_service.get_visible_team(session, user, team_id)
    return team_service.serialize_team(team)


@router.patch("/{team_id}", response_model=TeamResponse)
def update_team(
    team_id: uuid.UUID,
    body: TeamUpdate,
    user: CurrentUser,
    session: Annotated[Session, Depends(get_db)],
) -> TeamResponse:
    team = team_service.update_team(session, user, team_id, body)
    session.commit()
    return team_service.serialize_team(team)


@router.get("/{team_id}/members", response_model=list[EmployeeResponse])
def list_team_members(
    team_id: uuid.UUID,
    user: CurrentUser,
    session: Annotated[Session, Depends(get_db)],
) -> list[EmployeeResponse]:
    return team_service.list_team_members(session, user, team_id)
