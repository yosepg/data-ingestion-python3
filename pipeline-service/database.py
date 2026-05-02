"""
Database engine and session management for the pipeline service.
Creates tables automatically on startup.
"""

import os
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from models.customer import Base

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Connection setup
# ---------------------------------------------------------------------------

DATABASE_URL: str = os.environ.get(
    "DATABASE_URL",
    "postgresql://${POSTGRES_USER}:${POSTGRES_PASS}@localhost:${POSTGRES_PORT}/${POSTGRES_DATABASE}",
)

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,   # reconnect on stale connections
    pool_size=5,
    max_overflow=10,
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def init_db() -> None:
    """Create all tables defined in the ORM models (idempotent)."""
    logger.info("Initialising database schema …")
    Base.metadata.create_all(bind=engine)
    logger.info("Database schema ready.")


def get_db():
    """
    FastAPI dependency that yields a SQLAlchemy session and ensures it is
    closed after the request, even on error.
    """
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_db_connection() -> bool:
    """Return True if the database is reachable, False otherwise."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as exc:  # pragma: no cover
        logger.error("DB connection check failed: %s", exc)
        return False
