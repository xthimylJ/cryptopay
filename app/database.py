"""
Database connection.

SQLAlchemy is an ORM (Object-Relational Mapper): we describe tables as Python
classes (see models.py) and work with objects instead of writing raw SQL.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import settings

database_url = settings.DATABASE_URL
# Some hosts give "postgres://", SQLAlchemy expects "postgresql://".
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

# SQLite needs this flag because FastAPI may use the connection from
# different threads. PostgreSQL does not need it.
connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}

engine = create_engine(database_url, connect_args=connect_args, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    """Parent class for all ORM models."""


def get_db():
    """
    FastAPI dependency: opens one DB session per HTTP request and always
    closes it at the end, even if an error happened.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
