"""Create users table if not exists. Run from carmatch-backend: python init_db.py"""
import os
os.environ.setdefault("PGCLIENTENCODING", "UTF8")

# Hardcode URL to avoid psycopg2 UnicodeDecodeError when path/env has non-UTF-8 encoding on Windows
DATABASE_URL = "postgresql://carmatch:carmatch@localhost:5432/carmatch"

from sqlalchemy import create_engine
from src.database import Base
from src.models import User  # noqa: F401

if __name__ == "__main__":
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)
    Base.metadata.create_all(bind=engine)
    print("Tables created.")
