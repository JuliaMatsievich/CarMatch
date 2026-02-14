"""Проверка содержимого таблицы cars. Использует DATABASE_URL из .env или окружения."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main():
    from sqlalchemy import create_engine, text

    from src.config import settings

    url = settings.get_database_url()
    engine = create_engine(url)

    with engine.connect() as conn:
        # Количество записей
        count = conn.execute(text("SELECT COUNT(*) FROM cars")).scalar()
        print(f"Всего записей в cars: {count}")

        if count == 0:
            print("Таблица пустая.")
            return

        # Несколько первых строк (основные поля)
        result = conn.execute(
            text("""
                SELECT id, mark_name, model_name, body_type, year, price_rub, source
                FROM cars
                ORDER BY id
                LIMIT 10
            """)
        )
        rows = result.fetchall()
        print("\nПервые 10 записей (id, mark_name, model_name, body_type, year, price_rub, source):")
        for row in rows:
            print(" ", row._mapping)


if __name__ == "__main__":
    main()
