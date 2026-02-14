"""Показать поля (колонки) таблицы cars. Использует DATABASE_URL из .env или окружения."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main():
    from sqlalchemy import create_engine, text
    from src.config import settings

    url = settings.get_database_url()
    engine = create_engine(url)

    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = 'cars'
            ORDER BY ordinal_position
        """))
        rows = result.fetchall()
        print("Поля таблицы cars:")
        for r in rows:
            name, dtype, nullable, default = r
            default_str = f" DEFAULT {default}" if default else ""
            print(f"  {name}: {dtype} (nullable={nullable}){default_str}")


if __name__ == "__main__":
    main()
