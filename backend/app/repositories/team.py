"""Team persistence helpers."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.team import Team


def get_team_by_id(session: Session, team_id: uuid.UUID) -> Team | None:
    return session.scalar(
        select(Team).options(selectinload(Team.department), selectinload(Team.team_lead)).where(Team.id == team_id)
    )


def get_team_by_name(session: Session, organization_id: uuid.UUID, name: str) -> Team | None:
    return session.scalar(
        select(Team).where(Team.organization_id == organization_id, Team.name == name)
    )


def list_teams(session: Session, organization_id: uuid.UUID) -> list[Team]:
    statement = (
        select(Team)
        .options(selectinload(Team.department), selectinload(Team.team_lead))
        .where(Team.organization_id == organization_id)
        .order_by(Team.name)
    )
    return list(session.scalars(statement).unique())
