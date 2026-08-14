"""Refresh-token and access-token denylist persistence."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.auth_token import RefreshToken, RevokedAccessToken


def get_refresh_token_by_jti(session: Session, jti: str) -> RefreshToken | None:
    return session.scalar(select(RefreshToken).where(RefreshToken.jti == jti))


def add_refresh_token(
    session: Session,
    *,
    account_id: uuid.UUID,
    jti: str,
    token_hash: str,
    expires_at: datetime,
) -> RefreshToken:
    record = RefreshToken(
        account_id=account_id,
        jti=jti,
        token_hash=token_hash,
        expires_at=expires_at,
    )
    session.add(record)
    return record


def revoke_refresh_token(session: Session, record: RefreshToken) -> None:
    if record.revoked_at is None:
        record.revoked_at = datetime.now(timezone.utc)


def is_access_jti_revoked(session: Session, jti: str) -> bool:
    return session.scalar(select(RevokedAccessToken.id).where(RevokedAccessToken.jti == jti)) is not None


def revoke_access_jti(
    session: Session,
    *,
    account_id: uuid.UUID,
    jti: str,
    expires_at: datetime,
) -> None:
    if is_access_jti_revoked(session, jti):
        return
    session.add(
        RevokedAccessToken(
            account_id=account_id,
            jti=jti,
            expires_at=expires_at,
        )
    )
