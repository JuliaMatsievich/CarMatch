#!/usr/bin/env python3
"""
Однократный скрипт: обновляет cars.description в БД.
Запускать из папки carmatch-backend при работающей БД:
  python run_cars_description_migration.py
После успешного выполнения:  alembic stamp 5

Формат description: mark_name model_name (modification), body_type, year. <факты>
"""
import sys

from sqlalchemy import create_engine, text
from src.config import settings

SQL_UPDATE = """
UPDATE cars SET description = trim(BOTH ', ' FROM (
    mark_name || ' ' || model_name
    || CASE WHEN modification IS NOT NULL AND trim(modification) <> '' THEN ' (' || modification || ')' ELSE '' END
    || CASE WHEN body_type IS NOT NULL AND trim(body_type) <> '' THEN ', ' || body_type ELSE '' END
    || CASE WHEN year IS NOT NULL THEN ', ' || year::text ELSE '' END
    || CASE WHEN description IS NOT NULL AND trim(description) <> '' THEN '. ' || trim(description) ELSE '' END
))
"""


def main():
    url = settings.get_database_url()
    engine = create_engine(url, pool_pre_ping=True)
    try:
        with engine.begin() as conn:
            result = conn.execute(text(SQL_UPDATE))
            print(f"Обновлено строк cars: {result.rowcount}")
        print("Готово. Выполните:  alembic stamp 5")
    except Exception as e:
        print(f"Ошибка: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
