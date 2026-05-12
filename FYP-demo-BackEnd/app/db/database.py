import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL_ENV = os.getenv(
    "DATABASE_URL", "sqlite:///data/data.db"
)  # Default to SQLite if not set


def _ensure_sqlite_dir(database_url: str) -> None:
    """Create parent directory for SQLite files so engine init won't fail."""

    try:
        url = make_url(database_url)
    except Exception:
        return

    if url.get_backend_name() != "sqlite":
        return

    db_path = url.database
    if not db_path or db_path == ":memory:":
        return

    dir_path = Path(db_path).expanduser().parent
    if dir_path and not dir_path.exists():
        dir_path.mkdir(parents=True, exist_ok=True)


_ensure_sqlite_dir(DATABASE_URL_ENV)

# Determine if we are using SQLite based on the prefix
is_sqlite = DATABASE_URL_ENV.startswith("sqlite")

connect_args = {}
if is_sqlite:
    connect_args["check_same_thread"] = False  # Needed for SQLite for FastAPI

engine = create_engine(DATABASE_URL_ENV, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Function to create database tables
# This should be called once at application startup if tables don't exist
# For example, in main.py
def create_tables():
    # Import all models here before calling Base.metadata.create_all
    # This ensures they are registered with SQLAlchemy's metadata
    from .models import (
        ChatSession,
        ChatMessage,
        Character,
    )  # Adjust import if models are elsewhere

    Base.metadata.create_all(bind=engine)
