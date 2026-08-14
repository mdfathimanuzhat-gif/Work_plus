"""Authentication HTTP routes."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser, get_optional_access_payload
from app.database.session import get_db
from app.schemas.auth import (
    CurrentUserResponse,
    LoginRequest,
    LogoutRequest,
    MessageResponse,
    RefreshRequest,
    TokenResponse,
)
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, session: Annotated[Session, Depends(get_db)]) -> TokenResponse:
    tokens = auth_service.login(session, body.email, body.password)
    session.commit()
    return tokens


@router.post("/refresh", response_model=TokenResponse)
def refresh(body: RefreshRequest, session: Annotated[Session, Depends(get_db)]) -> TokenResponse:
    tokens = auth_service.refresh_tokens(session, body.refresh_token)
    session.commit()
    return tokens


@router.post("/logout", response_model=MessageResponse)
def logout(
    session: Annotated[Session, Depends(get_db)],
    access_payload: Annotated[dict | None, Depends(get_optional_access_payload)],
    body: LogoutRequest = LogoutRequest(),
) -> MessageResponse:
    auth_service.logout(session, access_payload=access_payload, refresh_token=body.refresh_token)
    session.commit()
    return MessageResponse(message="Logged out")


@router.get("/me", response_model=CurrentUserResponse)
def read_me(user: CurrentUser) -> CurrentUserResponse:
    return auth_service.serialize_current_user(user)
