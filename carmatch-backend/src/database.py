from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.types import JSON, TypeDecorator
from sqlalchemy.dialects.postgresql import ARRAY as PG_ARRAY, JSONB as PG_JSONB
from sqlalchemy import Text

from src.config import settings


class JSONBCompat(TypeDecorator):
    """JSON type: JSONB on PostgreSQL, JSON on SQLite (for tests)."""
    impl = JSON
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PG_JSONB())
        return dialect.type_descriptor(JSON())


class ArrayTextCompat(TypeDecorator):
    """Array of text: ARRAY(Text) on PostgreSQL, JSON (list) on SQLite (for tests)."""
    impl = JSON
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PG_ARRAY(Text()))
        return dialect.type_descriptor(JSON())

# В Docker: DATABASE_URL из env (postgres:5432). Локально: get_database_url() (ASCII)
engine = create_engine(
    settings.get_database_url(),
    pool_pre_ping=True,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
