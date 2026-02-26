"""PostgreSQL database connection and ORM setup."""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
import os
from typing import Generator

from app.db.models import Base

# Database configuration
DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "sqlite:///./vulnsentinel.db"  # Fallback for development
)

# Create engine with connection pooling
engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool if "postgres" in DATABASE_URL else None,
    pool_size=20 if "postgres" in DATABASE_URL else 5,
    max_overflow=40 if "postgres" in DATABASE_URL else 10,
    echo=os.getenv("SQL_ECHO", "false").lower() == "true"
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """Dependency for FastAPI to get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize database with all tables."""
    Base.metadata.create_all(bind=engine)
    print("✓ Database initialized successfully")


def drop_db():
    """Drop all tables (use with caution!)."""
    Base.metadata.drop_all(bind=engine)
    print("✓ Database dropped successfully")


def migrate_from_sqlite():
    """Migrate data from SQLite to PostgreSQL."""
    from sqlalchemy import inspect, text
    import shutil
    from datetime import datetime
    
    # This is a placeholder migration function
    # Actual migration would depend on existing data
    print("⚠ Migration from SQLite to PostgreSQL requires custom handling")
    print("  Please backup existing data before proceeding")
    
    if "sqlite" not in DATABASE_URL:
        print("✓ Already using PostgreSQL or equivalent")
        return True
    
    return False
