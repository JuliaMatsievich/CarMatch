from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from src.config import settings

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
