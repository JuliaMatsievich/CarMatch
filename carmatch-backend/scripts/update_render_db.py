"""
Обновить базу на Render целиком:
1. Применить миграции (alembic upgrade head)
2. Заполнить справочники из cars.xml (марки, модели, поколения и т.д.)
3. Скопировать таблицу cars с локальной БД на Render

Запуск (PowerShell) из папки carmatch-backend:
  $env:REMOTE_DATABASE_URL="postgresql://user:password@host/dbname?sslmode=require"
  python scripts/update_render_db.py

Локальная БД по умолчанию: localhost:5433/carmatch (где лежат ваши машины).
"""
import os
import subprocess
import sys

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND_DIR)

DEFAULT_LOCAL = "postgresql+psycopg://carmatch:carmatch@localhost:5433/carmatch"
REMOTE_URL = os.environ.get("REMOTE_DATABASE_URL", "").strip()
if not REMOTE_URL:
    print("Задайте REMOTE_DATABASE_URL (External Database URL с Render).")
    sys.exit(1)
if "postgresql+psycopg" not in REMOTE_URL:
    if REMOTE_URL.startswith("postgresql://"):
        REMOTE_URL = REMOTE_URL.replace("postgresql://", "postgresql+psycopg://", 1)
    elif REMOTE_URL.startswith("postgres://"):
        REMOTE_URL = REMOTE_URL.replace("postgres://", "postgresql+psycopg://", 1)

LOCAL_URL = os.environ.get("LOCAL_DATABASE_URL", "").strip() or DEFAULT_LOCAL
if "postgresql+psycopg" not in LOCAL_URL:
    if LOCAL_URL.startswith("postgresql://"):
        LOCAL_URL = LOCAL_URL.replace("postgresql://", "postgresql+psycopg://", 1)
    elif LOCAL_URL.startswith("postgres://"):
        LOCAL_URL = LOCAL_URL.replace("postgres://", "postgresql+psycopg://", 1)

env_remote = {**os.environ, "DATABASE_URL": REMOTE_URL}


def step(name, fn):
    print("\n---", name, "---")
    fn()
    print("OK.")


def run_migrations():
    r = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=BACKEND_DIR,
        env=env_remote,
    )
    if r.returncode != 0:
        sys.exit(r.returncode)


def run_seed():
    xml_path = os.path.join(os.path.dirname(BACKEND_DIR), "cars.xml")
    if not os.path.isfile(xml_path):
        print("Файл cars.xml не найден в корне проекта — пропускаем справочники.")
        return
    r = subprocess.run(
        [sys.executable, "seed_db.py"],
        cwd=BACKEND_DIR,
        env=env_remote,
    )
    if r.returncode != 0:
        sys.exit(r.returncode)


def copy_cars():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from src.models import Car

    engine_local = create_engine(LOCAL_URL, pool_pre_ping=True)
    engine_remote = create_engine(REMOTE_URL, pool_pre_ping=True)
    SessionLocal = sessionmaker(bind=engine_local)
    SessionRemote = sessionmaker(bind=engine_remote)
    local = SessionLocal()
    remote = SessionRemote()
    try:
        total = local.query(Car).count()
        print(f"Записей в cars (локально): {total}")
        if total == 0:
            print("Локально cars пустая — не копируем.")
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
                    brand_id=None,
                    model_id=None,
                    generation_id=None,
                    modification_id=None,
                )
                remote.add(c)
            remote.commit()
            copied += len(rows)
            print(f"  скопировано {copied} / {total}")
    finally:
        local.close()
        remote.close()


def main():
    print("Render DB:", REMOTE_URL.split("@")[-1] if "@" in REMOTE_URL else REMOTE_URL)
    print("Локальная БД (источник cars):", LOCAL_URL.split("@")[-1] if "@" in LOCAL_URL else LOCAL_URL)

    step("1. Миграции на Render", run_migrations)
    step("2. Справочники из cars.xml на Render", run_seed)
    step("3. Копирование cars с локальной БД на Render", copy_cars)

    print("\nГотово. База на Render обновлена.")


if __name__ == "__main__":
    main()
