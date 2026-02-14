"""
Копирование таблицы cars с локальной БД на Render.

Источник: LOCAL_DATABASE_URL в окружении или по умолчанию localhost:5433/carmatch.
Назначение: REMOTE_DATABASE_URL в окружении (External Database URL с Render).

Запуск (PowerShell):
  $env:REMOTE_DATABASE_URL="postgresql://...Render..."
  python scripts/copy_cars_to_render.py

Если локальная БД не на localhost:5433 — задайте:
  $env:LOCAL_DATABASE_URL="postgresql+psycopg://carmatch:carmatch@localhost:5433/carmatch"
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Локальная БД: явно из LOCAL_DATABASE_URL или значение по умолчанию (не из .env — там может быть Render)
DEFAULT_LOCAL = "postgresql+psycopg://carmatch:carmatch@localhost:5433/carmatch"
LOCAL_URL = os.environ.get("LOCAL_DATABASE_URL", "").strip() or DEFAULT_LOCAL
if "postgresql+psycopg" not in LOCAL_URL:
    if LOCAL_URL.startswith("postgresql://"):
        LOCAL_URL = LOCAL_URL.replace("postgresql://", "postgresql+psycopg://", 1)
    elif LOCAL_URL.startswith("postgres://"):
        LOCAL_URL = LOCAL_URL.replace("postgres://", "postgresql+psycopg://", 1)

_local_display = LOCAL_URL.split("@")[-1] if "@" in LOCAL_URL else LOCAL_URL
print(f"Источник (локальная БД): {_local_display}")

REMOTE_URL = os.environ.get("REMOTE_DATABASE_URL", "").strip()
if not REMOTE_URL:
    print("Задайте REMOTE_DATABASE_URL (External Database URL с Render).")
    print('Пример: $env:REMOTE_DATABASE_URL="postgresql://..."')
    sys.exit(1)

# Render даёт postgres:// — приводим к psycopg
if "postgresql+psycopg" not in REMOTE_URL:
    if REMOTE_URL.startswith("postgresql://"):
        REMOTE_URL = REMOTE_URL.replace("postgresql://", "postgresql+psycopg://", 1)
    elif REMOTE_URL.startswith("postgres://"):
        REMOTE_URL = REMOTE_URL.replace("postgres://", "postgresql+psycopg://", 1)


def main():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from src.database import Base
    from src.models import Car

    engine_local = create_engine(LOCAL_URL, pool_pre_ping=True)
    engine_remote = create_engine(REMOTE_URL, pool_pre_ping=True)

    SessionLocal = sessionmaker(bind=engine_local)
    SessionRemote = sessionmaker(bind=engine_remote)

    local = SessionLocal()
    remote = SessionRemote()

    try:
        total = local.query(Car).count()
        print(f"Записей в cars (локальная БД): {total}")
        if total == 0:
            print("Нечего копировать.")
            return

        BATCH = 500
        copied = 0
        for offset in range(0, total, BATCH):
            rows = local.query(Car).order_by(Car.id).offset(offset).limit(BATCH).all()
            for r in rows:
                c = Car(
                    source=r.source,
                    source_id=r.source_id,
                    mark_name=r.mark_name,
                    model_name=r.model_name,
                    body_type=r.body_type,
                    year=r.year,
                    price_rub=r.price_rub,
                    fuel_type=r.fuel_type,
                    engine_volume=r.engine_volume,
                    horsepower=r.horsepower,
                    modification=r.modification,
                    transmission=r.transmission,
                    specs=r.specs or {},
                    images=r.images,
                    description=r.description,
                    is_active=r.is_active,
                    # На Render справочники могут быть пустыми — не копируем FK
                    brand_id=None,
                    model_id=None,
                    generation_id=None,
                    modification_id=None,
                )
                remote.add(c)
            remote.commit()
            copied += len(rows)
            print(f"  скопировано {copied} / {total}")
        print("Готово.")
    finally:
        local.close()
        remote.close()


if __name__ == "__main__":
    main()
