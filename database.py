from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

SQLALCHEMY_DATABASE_URL = "sqlite:///./global360.db"


def utcnow() -> datetime:
    """Return current UTC time as a naive datetime.

    This replaces the deprecated ``datetime.utcnow()`` (removed in Python 3.17)
    with a compatible implementation that produces an equivalent *naive* datetime
    so SQLAlchemy / SQLite string serialization is unaffected.
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()