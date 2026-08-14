"""Authentication use cases: login, refresh, logout, current user."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import APIError
from app.core.security import (
    create_token,
    decode_token,
    hash_password,
    hash_token,
    validate_password_strength,
    verify_password,
)
from app.models.user_account import UserAccount
from app.repositories import token as token_repository
from app.repositories import user_account as account_repository
from app.schemas.auth import CurrentUserResponse, TokenResponse
from app.services.authorization import AuthenticatedUser

_DUMMY_PASSWORD_HASH: str | None = None


def _invalid_credentials() -> None:
    raise APIError(401, "invalid_credentials", "Invalid email or password")


def _dummy_hash() -> str:
    global _DUMMY_PASSWORD_HASH
    if _DUMMY_PASSWORD_HASH is None:
        _DUMMY_PASSWORD_HASH = hash_password("WorkPulseDummyHash9")
    return _DUMMY_PASSWORD_HASH


def _is_account_usable(account: UserAccount) -> bool:
    return account.is_active and account.employee.is_active


def _roles_and_permissions(account: UserAccount) -> tuple[tuple[str, ...], frozenset[str]]:
    roles = tuple(assignment.role.name for assignment in account.employee.employee_roles)
    permissions: set[str] = set()
    for assignment in account.employee.employee_roles:
        permissions.update(permission.name for permission in assignment.role.permissions)
    return roles, frozenset(permissions)


def build_authenticated_user(account: UserAccount) -> AuthenticatedUser:
    roles, permissions = _roles_and_permissions(account)
    return AuthenticatedUser(
        account=account,
        employee=account.employee,
        roles=roles,
        permissions=permissions,
    )


def issue_token_pair(session: Session, user: AuthenticatedUser) -> TokenResponse:
    settings = get_settings()
    access_token, _, _ = create_token(
        account_id=user.account_id,
        employee_id=user.employee_id,
        organization_id=user.organization_id,
        role=user.primary_role,
        roles=list(user.roles),
        token_type="access",
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    refresh_token, refresh_jti, refresh_expires = create_token(
        account_id=user.account_id,
        employee_id=user.employee_id,
        organization_id=user.organization_id,
        role=user.primary_role,
        roles=list(user.roles),
        token_type="refresh",
        expires_delta=timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )
    token_repository.add_refresh_token(
        session,
        account_id=user.account_id,
        jti=refresh_jti,
        token_hash=hash_token(refresh_token),
        expires_at=refresh_expires,
    )
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


def create_account(
    session: Session,
    *,
    employee_id: uuid.UUID,
    email: str,
    password: str,
    is_active: bool = True,
) -> UserAccount:
    validate_password_strength(password)
    normalized_email = email.strip().lower()
    if account_repository.get_account_by_email(session, normalized_email) is not None:
        raise APIError(409, "account_exists", "An account already exists for this email")
    account = UserAccount(
        employee_id=employee_id,
        email=normalized_email,
        password_hash=hash_password(password),
        is_active=is_active,
    )
    session.add(account)
    session.flush()
    return account


def login(session: Session, email: str, password: str) -> TokenResponse:
    account = account_repository.get_account_by_email(session, email.strip().lower())
    password_hash = account.password_hash if account is not None else _dummy_hash()
    password_ok = verify_password(password, password_hash)
    if account is None or not password_ok or not _is_account_usable(account):
        _invalid_credentials()

    loaded = account_repository.get_account_with_authorization(session, account.id)
    if loaded is None or not _is_account_usable(loaded):
        _invalid_credentials()
    loaded.last_login_at = datetime.now(timezone.utc)
    user = build_authenticated_user(loaded)
    return issue_token_pair(session, user)


def refresh_tokens(session: Session, refresh_token: str) -> TokenResponse:
    payload = decode_token(refresh_token, "refresh")
    record = token_repository.get_refresh_token_by_jti(session, str(payload.get("jti", "")))
    now = datetime.now(timezone.utc)
    if (
        record is None
        or record.revoked_at is not None
        or record.expires_at < now
        or record.token_hash != hash_token(refresh_token)
    ):
        raise APIError(401, "invalid_token", "Invalid token")

    token_repository.revoke_refresh_token(session, record)
    account = account_repository.get_account_with_authorization(session, record.account_id)
    if account is None or not _is_account_usable(account):
        raise APIError(401, "invalid_credentials", "Invalid email or password")
    return issue_token_pair(session, build_authenticated_user(account))


def logout(
    session: Session,
    *,
    access_payload: dict | None,
    refresh_token: str | None,
) -> None:
    if refresh_token:
        try:
            payload = decode_token(refresh_token, "refresh")
        except APIError:
            payload = None
        if payload is not None:
            record = token_repository.get_refresh_token_by_jti(session, str(payload.get("jti", "")))
            if record is not None:
                token_repository.revoke_refresh_token(session, record)

    if access_payload is not None:
        expires_at = datetime.fromtimestamp(int(access_payload["exp"]), tz=timezone.utc)
        token_repository.revoke_access_jti(
            session,
            account_id=uuid.UUID(str(access_payload["sub"])),
            jti=str(access_payload["jti"]),
            expires_at=expires_at,
        )


def serialize_current_user(user: AuthenticatedUser) -> CurrentUserResponse:
    employee = user.employee
    return CurrentUserResponse(
        account_id=user.account_id,
        employee_id=user.employee_id,
        organization_id=user.organization_id,
        email=user.account.email,
        first_name=employee.first_name,
        last_name=employee.last_name,
        employee_code=employee.employee_code,
        team_id=employee.team_id,
        department_id=employee.department_id,
        roles=list(user.roles),
        permissions=sorted(user.permissions),
        last_login_at=user.account.last_login_at,
    )
