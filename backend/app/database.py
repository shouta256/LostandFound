"""Shared SQLAlchemy connection and session setup; no tables are created here."""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import Settings

engine = create_engine(Settings().database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine)


class Base(DeclarativeBase):
    """Base class for future database models."""


def get_db() -> Generator[Session, None, None]:
    """Own one request session; FastAPI runs this sync dependency in workers.

    Callers explicitly commit successful transactions. The session is used
    sequentially within the request, never concurrently by multiple tasks.
    """
    with SessionLocal() as session:
        try:
            yield session
        except Exception:
            session.rollback()
            raise
