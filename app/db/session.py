from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator

from app.core.config import settings
from app.models.models import Base

# Create the SQLAlchemy engine
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,   # verify connection health before checkout
    pool_size=10,
    max_overflow=20,
    echo=settings.DEBUG,  # log SQL when DEBUG=True
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def create_tables() -> None:
    """Create all tables (used for test setup / initial deployment)."""
    Base.metadata.create_all(bind=engine)


def drop_tables() -> None:
    """Drop all tables (test teardown only)."""
    Base.metadata.drop_all(bind=engine)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency: yields a database session and ensures it is closed."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
