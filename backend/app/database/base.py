"""Declarative base for SQLAlchemy models.

Alembic imports this metadata. Domain models will be added in later phases.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Shared declarative base for all persistence models."""
