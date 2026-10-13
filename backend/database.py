"""SQLAlchemy Database configuration and session management for GrihaValue.

Supports SQLite for self-contained local development and testing,
and PostgreSQL for production environments via DATABASE_URL.
"""

from __future__ import annotations

import os
from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from backend.config import ROOT_DIR

# Default to local SQLite database in backend/data/
DEFAULT_SQLITE_PATH = ROOT_DIR / "backend" / "data" / "estateiq.db"
DEFAULT_DB_URL = f"sqlite:///{DEFAULT_SQLITE_PATH.as_posix()}"

DATABASE_URL = os.environ.get("DATABASE_URL", DEFAULT_DB_URL)

# Ensure data directory exists if using SQLite
if DATABASE_URL.startswith("sqlite"):
    DEFAULT_SQLITE_PATH.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        echo=False,
    )
else:
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
        echo=False,
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy declarative models."""
    pass


def get_db_session() -> Generator[Session, None, None]:
    """Provide a transactional database session."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
