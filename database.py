import os
from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Read the database URL directly from environment variables (No hardcoded paths)
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL")

if not SQLALCHEMY_DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is not set!")

# Normalize the legacy "postgres://" scheme that platforms like Render hand out;
# SQLAlchemy 2.x only recognizes "postgresql://" and will fail to load the dialect.
if SQLALCHEMY_DATABASE_URL.startswith("postgres://"):
    SQLALCHEMY_DATABASE_URL = SQLALCHEMY_DATABASE_URL.replace(
        "postgres://", "postgresql://", 1
    )

def utcnow() -> datetime:
    """Return current UTC time as a naive datetime."""
    return datetime.now(timezone.utc).replace(tzinfo=None)

# Handle connect_args only for SQLite engines dynamically
connect_args = {"check_same_thread": False} if SQLALCHEMY_DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()