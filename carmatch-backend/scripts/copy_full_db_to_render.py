"""
Скопировать всю локальную БД на Render (без cars.xml).

1. Применить миграции на Render.
2. Очистить таблицы на Render и перенести все данные из локальной БД.

Порядок таблиц учитывает внешние ключи.
Запуск (PowerShell) из carmatch-backend:
  $env:REMOTE_DATABASE_URL="postgresql://...Render..."
  python scripts/copy_full_db_to_render.py
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
for prefix in ("postgresql://", "postgres://"):
    if REMOTE_URL.startswith(prefix) and "postgresql+psycopg" not in REMOTE_URL:
        REMOTE_URL = REMOTE_URL.replace(prefix, "postgresql+psycopg://", 1)
        break

LOCAL_URL = os.environ.get("LOCAL_DATABASE_URL", "").strip() or DEFAULT_LOCAL
for prefix in ("postgresql://", "postgres://"):
    if LOCAL_URL.startswith(prefix) and "postgresql+psycopg" not in LOCAL_URL:
        LOCAL_URL = LOCAL_URL.replace(prefix, "postgresql+psycopg://", 1)
        break

env_remote = {**os.environ, "DATABASE_URL": REMOTE_URL}

# Порядок таблиц по зависимостям (FK)
MODELS_ORDER = [
    "User", "CarBrand", "CarModel", "CarGeneration", "CarModification", "CarComplectation",
    "Session", "Car", "ChatMessage", "SearchParameter",
]


def run_migrations():
    print("Миграции на Render...")
    r = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=BACKEND_DIR,
        env=env_remote,
    )
    if r.returncode != 0:
        sys.exit(r.returncode)
    print("OK.\n")


def row_to_dict(row):
    return {c.key: getattr(row, c.key) for c in row.__table__.c}


def copy_full_db():
    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import sessionmaker

    import src.models as models  # noqa: F401

    engine_local = create_engine(LOCAL_URL, pool_pre_ping=True)
    engine_remote = create_engine(REMOTE_URL, pool_pre_ping=True)
    Local = sessionmaker(bind=engine_local)
    Remote = sessionmaker(bind=engine_remote)
    local = Local()
    remote = Remote()

    try:
        # Очистить все таблицы на Render: users, sessions, car_brands — CASCADE очистит остальные
        print("Очистка таблиц на Render...")
        remote.execute(text('TRUNCATE TABLE users, sessions, car_brands RESTART IDENTITY CASCADE;'))
        remote.commit()
        print("OK.\n")

        # Копировать данные по таблицам (крупные — батчами с прогрессом)
        BATCH_SIZE = 2000
        for name in MODELS_ORDER:
            model = getattr(models, name)
            table = model.__table__.name
            total = local.query(model).count()
            if total == 0:
                print(f"  {table}: 0 записей")
                continue
            if total <= BATCH_SIZE:
                rows = local.query(model).all()
                dicts = [row_to_dict(r) for r in rows]
                remote.bulk_insert_mappings(model, dicts)
                remote.commit()
                print(f"  {table}: {total} записей")
            else:
                copied = 0
                offset = 0
                while offset < total:
                    pk = list(model.__table__.primary_key.columns)[0]
                    rows = local.query(model).order_by(pk).offset(offset).limit(BATCH_SIZE).all()
                    if not rows:
                        break
                    dicts = [row_to_dict(r) for r in rows]
                    remote.bulk_insert_mappings(model, dicts)
                    remote.commit()
                    copied += len(rows)
                    offset += BATCH_SIZE
                    print(f"  {table}: {copied} / {total}")
                print(f"  {table}: всего {copied} записей")

        # alembic_version
        ver = local.execute(text("SELECT version_num FROM alembic_version")).fetchone()
        if ver:
            remote.execute(text("DELETE FROM alembic_version"))
            remote.execute(text("INSERT INTO alembic_version (version_num) VALUES (:v)"), {"v": ver[0]})
            remote.commit()
            print("  alembic_version: скопирована")

        # Обновить последовательности на Render (чтобы новые вставки получали корректные id)
        print("\nОбновление последовательностей...")
        for table, col in [
            ("users", "id"), ("car_brands", "id"), ("car_models", "id"),
            ("car_generations", "id"), ("car_modifications", "id"), ("car_complectations", "id"),
            ("cars", "id"), ("chat_messages", "id"), ("search_parameters", "id"),
        ]:
            try:
                max_id = remote.execute(text(f'SELECT COALESCE(MAX("{col}"), 0) FROM "{table}"')).scalar()
                if max_id and max_id > 0:
                    remote.execute(text("SELECT setval(pg_get_serial_sequence(:t, :c), :m)"), {"t": table, "c": col, "m": max_id})
            except Exception:
                pass
        remote.commit()
        print("Готово.")
    finally:
        local.close()
        remote.close()


def main():
    print("Локальная БД:", LOCAL_URL.split("@")[-1] if "@" in LOCAL_URL else LOCAL_URL)
    print("Render БД:", REMOTE_URL.split("@")[-1] if "@" in REMOTE_URL else REMOTE_URL, "\n")

    run_migrations()
    copy_full_db()
    print("\nВся база перенесена на Render.")


if __name__ == "__main__":
    main()
