"""Database connection and session management — SQLite & MySQL."""

import logging
import sys

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session

from config import DATABASE_URL

logger = logging.getLogger("fund-analyzer")

_dialect = DATABASE_URL.split("://")[0] if "://" in DATABASE_URL else "sqlite"

if _dialect in ("mysql", "mysql+pymysql"):
    logger.info("MySQL dialect detected, initializing connection pool...")
    try:
        # auto-create database if needed
        _base_url = DATABASE_URL.rsplit("/", 1)[0]  # strip /dbname
        _db_name = DATABASE_URL.rsplit("/", 1)[-1].split("?")[0]
        logger.info("Ensuring database '%s' exists...", _db_name)
        _base_engine = create_engine(_base_url, connect_args={"connect_timeout": 10})
        with _base_engine.connect() as conn:
            conn.execute(text(
                f"CREATE DATABASE IF NOT EXISTS `{_db_name}` "
                "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            ))
            conn.commit()
        _base_engine.dispose()
        logger.info("Database '%s' is ready.", _db_name)

        engine = create_engine(
            DATABASE_URL,
            pool_size=5,
            max_overflow=5,
            pool_recycle=300,
            pool_pre_ping=True,
        )
        # Verify the connection works immediately
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("MySQL connection pool established successfully.")
    except Exception as e:
        logger.error("MySQL connection failed: %s", e)
        sys.exit(1)
else:
    logger.info("SQLite dialect detected, using file-based database.")
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Session:
    """Get a database session. Caller is responsible for closing it."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Create all tables if they don't exist."""
    from models import Base
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables verified.")
