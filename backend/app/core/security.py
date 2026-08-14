"""Password hashing and JWT helpers. Never log secrets or tokens."""

from __future__ import annotations

import hashlib
import re
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Literal

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

from app.core.config import get_settings
from app.core.errors import APIError

_hasher = PasswordHasher()
_PASSWORD_LETTER = re.compile(r"[A-Za-z]")
_PASSWORD_DIGIT = re.compile(r"\d")
MIN_PASSWORD_LENGTH = 10

TokenType = Literal["access", "refresh", "device"]


def hash_password(plain_password: str) -> str:
    return _hasher.hash(plain_password)


def verify_password(plain_password: str, password_hash: str) -> bool:
    try:
        return _hasher.verify(password_hash, plain_password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def validate_password_strength(plain_password: str) -> None:
    if len(plain_password) < MIN_PASSWORD_LENGTH:
        raise APIError(
            422,
            "weak_password",
            f"Password must be at least {MIN_PASSWORD_LENGTH} characters",
        )
    if _PASSWORD_LETTER.search(plain_password) is None or _PASSWORD_DIGIT.search(plain_password) is None:
        raise APIError(422, "weak_password", "Password must include at least one letter and one number")


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def create_token(
    *,
    account_id: uuid.UUID,
    employee_id: uuid.UUID,
    organization_id: uuid.UUID,
    role: str,
    roles: list[str],
    token_type: TokenType,
    expires_delta: timedelta,
    jti: str | None = None,
) -> tuple[str, str, datetime]:
    settings = get_settings()
    now = _utcnow()
    expires_at = now + expires_delta
    token_jti = jti or str(uuid.uuid4())
    payload: dict[str, Any] = {
        "sub": str(account_id),
        "employee_id": str(employee_id),
        "organization_id": str(organization_id),
        "role": role,
        "roles": roles,
        "typ": token_type,
        "jti": token_jti,
        "iat": int(now.timestamp()),
        "exp": int(expires_at.timestamp()),
    }
    encoded = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return encoded, token_jti, expires_at


def create_device_token(
    *,
    device_id: uuid.UUID,
    employee_id: uuid.UUID,
    organization_id: uuid.UUID,
    device_identifier: str,
    expires_delta: timedelta,
    jti: str | None = None,
) -> tuple[str, str, datetime]:
    settings = get_settings()
    now = _utcnow()
    expires_at = now + expires_delta
    token_jti = jti or str(uuid.uuid4())
    payload: dict[str, Any] = {
        "sub": str(device_id),
        "employee_id": str(employee_id),
        "organization_id": str(organization_id),
        "device_identifier": device_identifier,
        "typ": "device",
        "jti": token_jti,
        "iat": int(now.timestamp()),
        "exp": int(expires_at.timestamp()),
    }
    encoded = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return encoded, token_jti, expires_at


def decode_token(token: str, expected_type: TokenType) -> dict[str, Any]:
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except jwt.ExpiredSignatureError as exc:
        raise APIError(401, "token_expired", "Token has expired") from exc
    except jwt.InvalidTokenError as exc:
        raise APIError(401, "invalid_token", "Invalid token") from exc

    if payload.get("typ") != expected_type:
        raise APIError(401, "invalid_token", "Invalid token")
    return payload
