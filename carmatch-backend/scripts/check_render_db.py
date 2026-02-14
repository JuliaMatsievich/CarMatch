"""Проверка текущей ревизии Alembic и списка таблиц в БД. Запуск из carmatch-backend с DATABASE_URL в env."""
import os
import sys

# чтобы подтянуть src.config
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def main():
    from sqlalchemy import create_engine, text
    from src.config import settings

    url = settings.get_database_url()
    # не показываем пароль в логах
    safe_url = url.split("@")[-1] if "@" in url else url
    print("Подключение к БД:", safe_url)

    engine = create_engine(url)
    with engine.connect() as conn:
        # Текущая ревизия Alembic
        try:
            row = conn.execute(text("SELECT version_num FROM alembic_version")).fetchone()
            print("Текущая ревизия Alembic:", row[0] if row else "(таблицы alembic_version нет)")
        except Exception as e:
            print("Ошибка при чтении alembic_version:", e)

        # Список таблиц
        try:
            result = conn.execute(text("""
                SELECT table_name FROM information_schema.tables
                WHERE table_schema = 'public'
                ORDER BY table_name
            """))
            tables = [r[0] for r in result]
            print("Таблицы в public:", ", ".join(tables) if tables else "(нет таблиц)")
        except Exception as e:
            print("Ошибка при списке таблиц:", e)

if __name__ == "__main__":
    main()
