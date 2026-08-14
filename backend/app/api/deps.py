"""FastAPI dependencies for authentication and authorization."""

from __future__ import annotations

import uuid
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.errors import APIError
from app.core.security import decode_token
from app.database.session import get_db
from app.repositories import token as token_repository
from app.repositories import user_account as account_repository
from app.services.auth_service import build_authenticated_user
from app.services.authorization import AuthenticatedUser, require_permission, require_role

bearer_scheme = HTTPBearer(auto_error=False)
DbSession = Annotated[Session, Depends(get_db)]


def _credentials_token(
    credentials: HTTPAuthorizationCredentials | None,
) -> str:
    if credentials is None or credentials.scheme.lower() != "bearer" or not credentials.credentials:
        raise APIError(401, "not_authenticated", "Authentication required")
    return credentials.credentials


def get_access_payload(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> dict:
    token = _credentials_token(credentials)
    return decode_token(token, "access")


def get_optional_access_payload(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> dict | None:
    if credentials is None or not credentials.credentials:
        return None
    try:
        return decode_token(credentials.credentials, "access")
    except APIError:
        return None


def require_authenticated_user(
    session: DbSession,
    payload: Annotated[dict, Depends(get_access_payload)],
) -> AuthenticatedUser:
    jti = str(payload.get("jti", ""))
    if not jti or token_repository.is_access_jti_revoked(session, jti):
        raise APIError(401, "invalid_token", "Invalid token")

    expires_at = datetime.fromtimestamp(int(payload["exp"]), tz=timezone.utc)
    if expires_at < datetime.now(timezone.utc):
        raise APIError(401, "token_expired", "Token has expired")

    try:
        account_id = uuid.UUID(str(payload["sub"]))
    except (KeyError, ValueError) as exc:
        raise APIError(401, "invalid_token", "Invalid token") from exc

    account = account_repository.get_account_with_authorization(session, account_id)
    if account is None or not account.is_active or not account.employee.is_active:
        raise APIError(401, "invalid_token", "Invalid token")
    return build_authenticated_user(account)


CurrentUser = Annotated[AuthenticatedUser, Depends(require_authenticated_user)]


def require_role_dep(*role_names: str) -> Callable[[CurrentUser], AuthenticatedUser]:
    def dependency(user: CurrentUser) -> AuthenticatedUser:
        require_role(user, *role_names)
        return user

    return dependency


def require_permission_dep(*permission_names: str) -> Callable[[CurrentUser], AuthenticatedUser]:
    def dependency(user: CurrentUser) -> AuthenticatedUser:
        require_permission(user, *permission_names)
        return user

    return dependency
