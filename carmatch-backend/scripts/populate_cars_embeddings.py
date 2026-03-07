"""
Заполнение колонки cars.embedding через Yandex Cloud Embeddings API.

Читает из БД активные автомобили (или по фильтру), для каждого формирует текст
из mark_name, model_name, modification, body_type, year, description и получает
вектор эмбеддинга (256) от Yandex, затем обновляет запись в БД.

Требуется в .env:
  YANDEX_FOLDER_ID=...   # ID каталога в Yandex Cloud
  YANDEX_API_KEY=...    # API-ключ сервисного аккаунта с ролью ai.languageModels.user
  DATABASE_URL=...       # подключение к PostgreSQL с pgvector

Запуск из корня carmatch-backend:
  python scripts/populate_cars_embeddings.py
  python scripts/populate_cars_embeddings.py --limit 100
  python scripts/populate_cars_embeddings.py --force   # перезаписать все эмбеддинги
"""
import argparse
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# DATABASE_URL из окружения или .env через pydantic-settings
from sqlalchemy import text

from src.config import settings
from src.database import SessionLocal
from src.models import Car
from src.services.yandex_embeddings import get_embedding
from src.utils.car_display import format_car_description


def text_for_embedding(car: Car) -> str:
    """Текст для эмбеддинга: описание авто (марка, модель, модификация, кузов, год, описание)."""
    s = format_car_description(car)
    if s and s.strip():
        return s.strip()
    parts = [getattr(car, "mark_name", "") or "", getattr(car, "model_name", "") or ""]
    return " ".join(p for p in parts if p).strip() or "Автомобиль"


def main() -> None:
    parser = argparse.ArgumentParser(description="Заполнить cars.embedding через Yandex Embeddings API")
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Максимум записей обработать (0 = без ограничений)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Обновить эмбеддинги даже там, где они уже заполнены",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.2,
        help="Задержка между запросами к API в секундах (по умолчанию 0.2)",
    )
    args = parser.parse_args()

    if not settings.yandex_folder_id or not settings.yandex_api_key:
        print("Ошибка: задайте YANDEX_FOLDER_ID и YANDEX_API_KEY в .env")
        print("Подробнее: см. EMBEDDINGS.md")
        sys.exit(1)

    db_url = settings.get_database_url()
    if "postgresql" not in db_url:
        print("Ошибка: скрипт предназначен для PostgreSQL с pgvector. DATABASE_URL:", db_url[:50], "...")
        sys.exit(1)

    session = SessionLocal()
    try:
        q = session.query(Car).filter(Car.is_active == True)
        if not args.force:
            q = q.filter(Car.embedding.is_(None))
        q = q.order_by(Car.id)
        if args.limit:
            q = q.limit(args.limit)
        cars = q.all()
    finally:
        session.close()

    total = len(cars)
    if total == 0:
        print("Нет записей для обработки (все уже с эмбеддингами или нет активных cars).")
        print("Используйте --force чтобы перезаписать все эмбеддинги.")
        return

    print(f"Будет обработано записей: {total}")
    print(f"Задержка между запросами: {args.delay} с")
    ok = 0
    err = 0
    session = SessionLocal()
    try:
        for i, car in enumerate(cars, 1):
            text_to_embed = text_for_embedding(car)
            emb = get_embedding(text_to_embed)
            if emb is None:
                err += 1
                print(f"  [{i}/{total}] id={car.id} — ошибка получения эмбеддинга")
                if args.delay:
                    time.sleep(args.delay)
                continue
            # Обновляем через raw SQL, чтобы избежать ошибки pgvector "posting list tuple cannot be split"
            emb_str = "[" + ",".join(str(x) for x in emb) + "]"
            session.execute(
                text("UPDATE cars SET embedding = CAST(:emb AS vector), updated_at = now() WHERE id = :id"),
                {"emb": emb_str, "id": car.id},
            )
            session.commit()
            ok += 1
            if i % 50 == 0 or i == total:
                print(f"  Обработано {i}/{total}, OK: {ok}, ошибок: {err}")
            if args.delay:
                time.sleep(args.delay)
    finally:
        session.close()

    print(f"Готово. Успешно: {ok}, ошибок: {err}")


if __name__ == "__main__":
    main()
