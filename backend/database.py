"""Database connection and session management — SQLite & MySQL."""

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session

from config import DATABASE_URL

_dialect = DATABASE_URL.split("://")[0] if "://" in DATABASE_URL else "sqlite"

if _dialect in ("mysql", "mysql+pymysql"):
    # MySQL: auto-create database if needed
    _base_url = DATABASE_URL.rsplit("/", 1)[0]  # strip /dbname
    _db_name = DATABASE_URL.rsplit("/", 1)[-1].split("?")[0]
    _base_engine = create_engine(_base_url)
    with _base_engine.connect() as conn:
        conn.execute(text(f"CREATE DATABASE IF NOT EXISTS `{_db_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"))
        conn.commit()
    _base_engine.dispose()
    engine = create_engine(DATABASE_URL)
else:
    # SQLite
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
