# CarMatch Backend

API авторизации (регистрация и вход). PostgreSQL и API в Docker.

## Запуск (рекомендуется — всё в Docker)

```bash
docker compose up -d
```

Поднимаются:

- **postgres** — порт 5432, БД carmatch, пользователь/пароль carmatch
- **api** — порт 8000, при старте выполняет миграции и запускает uvicorn

API: http://localhost:8000  
Документация: http://localhost:8000/docs  
Эндпоинты: `POST /api/v1/auth/register`, `POST /api/v1/auth/login`.

**Важно:** если на порту 8000 уже запущен другой процесс (например, старый uvicorn), остановите его — иначе запросы будут уходить не в Docker API.

## Локальный запуск (без Docker API)

1. PostgreSQL: `docker compose up -d postgres`
2. Таблица: `docker exec carmatch-postgres psql -U carmatch -d carmatch -c "CREATE TABLE IF NOT EXISTS users (...);"` (см. полный DDL в разделе 5 спецификации)
3. `.env`: `DATABASE_URL=postgresql+psycopg://carmatch:carmatch@localhost:5432/carmatch`
4. `pip install -r requirements.txt && python -m uvicorn main:app --reload --port 8000`

На Windows при ошибке `UnicodeDecodeError` в psycopg2 используйте Docker (см. выше) или драйвер psycopg3 (в коде уже используется `postgresql+psycopg`).

## Тестирование

```bash
pip install -r requirements.txt
pytest
```

Тесты используют SQLite in-memory, PostgreSQL не требуется.
