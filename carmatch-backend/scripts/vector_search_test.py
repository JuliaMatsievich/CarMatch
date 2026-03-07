"""
Проверка векторного поиска по cars: запрос → эмбеддинг запроса (text-search-query) → поиск по косинусной близости.
По умолчанию выводит топ-5 подходящих машин.

Запуск из корня carmatch-backend:
  python scripts/vector_search_test.py "Текст запроса"
  python scripts/vector_search_test.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text

from src.config import settings
from src.database import SessionLocal
from src.services.yandex_embeddings import get_query_embedding


def vector_search(query_text: str, limit: int = 5):
    """Поиск машин по смыслу запроса (косинусное расстояние, pgvector)."""
    emb = get_query_embedding(query_text)
    if emb is None:
        return None, "Не удалось получить эмбеддинг запроса (проверьте YANDEX_FOLDER_ID, YANDEX_API_KEY и доступ к API)."

    # Строка вектора для PostgreSQL: '[0.1,0.2,...]'
    vec_str = "[" + ",".join(str(x) for x in emb) + "]"

    session = SessionLocal()
    try:
        # pgvector: <=> — косинусное расстояние (меньше = ближе)
        result = session.execute(
            text("""
                SELECT id, mark_name, model_name, body_type, year, description,
                       (embedding <=> CAST(:qv AS vector)) AS distance
                FROM cars
                WHERE is_active = true AND embedding IS NOT NULL
                ORDER BY embedding <=> CAST(:qv AS vector)
                LIMIT :lim
            """),
            {"qv": vec_str, "lim": limit},
        )
        rows = result.fetchall()
        return rows, None
    except Exception as e:
        return None, str(e)
    finally:
        session.close()


def main():
    query = " ".join(sys.argv[1:]).strip() if len(sys.argv) > 1 else (
        "Ключи от какой машины в одном из шоу талантов победителю вручили ключи и позже её мельком показали в ситкоме"
    )

    if not settings.yandex_folder_id or not settings.yandex_api_key:
        print("Ошибка: задайте YANDEX_FOLDER_ID и YANDEX_API_KEY в .env")
        sys.exit(1)

    print("Запрос:", query)
    print()
    rows, err = vector_search(query, limit=5)
    if err:
        print("Ошибка:", err)
        sys.exit(1)
    if not rows:
        print("Нет машин с заполненным эмбеддингом. Запустите: python scripts/populate_cars_embeddings.py")
        sys.exit(0)

    print(f"Найдено по векторному поиску (топ-5):")
    print("-" * 80)
    for i, r in enumerate(rows, 1):
        desc = (r.description or "")[:120]
        if len((r.description or "")) > 120:
            desc += "..."
        print(f"{i}. [{r.distance:.4f}] {r.mark_name} {r.model_name} ({r.body_type or '-'}, {r.year or '-'})")
        if desc:
            print(f"   {desc}")
        print()
    print("(distance — косинусное расстояние: меньше = ближе по смыслу)")


if __name__ == "__main__":
    main()
