# CarMatch Backend

API авторизации (регистрация и вход). PostgreSQL и API в Docker.

## Запуск (рекомендуется — всё в Docker)

```bash
docker compose up -d
```

Поднимаются:

- **postgres** — с хоста порт **5433** (в контейнере 5432), БД carmatch, пользователь/пароль carmatch
- **api** — порт 8000, при старте выполняет миграции и запускает uvicorn

API: http://localhost:8000  
Документация: http://localhost:8000/docs  
Эндпоинты: `POST /api/v1/auth/register`, `POST /api/v1/auth/login`, `POST /api/v1/chat/complete` (чат с GigaChat). Админ-API см. ниже.

## Админ-панель (API)

Эндпоинты админки требуют авторизации с ролью администратора (Bearer-токен пользователя с `is_admin=true`).

- **Пользователи** — `GET /api/v1/admin/users` (список с пагинацией и фильтрами), `GET /api/v1/admin/users/{user_id}` (профиль), `DELETE /api/v1/admin/users/{user_id}`
- **Автомобили** — `GET /api/v1/admin/cars`, `GET /api/v1/admin/cars/{car_id}`, `POST /api/v1/admin/cars`, `PUT /api/v1/admin/cars/{car_id}`, `DELETE /api/v1/admin/cars/{car_id}`
- **Сессии чата (диалоги)** — `GET /api/v1/admin/sessions` (список), `GET /api/v1/admin/sessions/{session_id}` (детали и сообщения), `DELETE /api/v1/admin/sessions/{session_id}`

Учётная запись администратора создаётся миграциями (см. `alembic/versions/`); по умолчанию логин/пароль можно посмотреть в seed-миграции.

**Важно:** если на порту 8000 уже запущен другой процесс (например, старый uvicorn), остановите его — иначе запросы будут уходить не в Docker API. Если в Swagger (/docs) нет эндпоинта `POST /api/v1/chat/complete`, пересоберите образ: `docker compose build --no-cache api && docker compose up -d`.

## Локальный запуск (без Docker API)

1. **Перейдите в папку бэкенда:** `cd carmatch-backend` (uvicorn должен запускаться именно отсюда).
2. PostgreSQL: `docker compose up -d postgres`
3. Таблица: `docker exec carmatch-postgres psql -U carmatch -d carmatch -c "CREATE TABLE IF NOT EXISTS users (...);"` (см. полный DDL в разделе 5 спецификации)
4. `.env`: `DATABASE_URL=postgresql+psycopg://carmatch:carmatch@localhost:5433/carmatch` (БД на порту 5433)
5. `pip install -r requirements.txt && python -m uvicorn main:app --reload --port 8000`

При старте в консоли выводятся все маршруты; среди них должен быть `POST /api/v1/chat/complete`. Если его нет — вы запустили uvicorn не из папки `carmatch-backend`.

На Windows при ошибке `UnicodeDecodeError` в psycopg2 используйте Docker (см. выше) или драйвер psycopg3 (в коде уже используется `postgresql+psycopg`).

### GigaChat (чат)

Чтобы работал эндпоинт свободного чата `POST /api/v1/chat/complete`, в `.env` задайте ключ авторизации GigaChat:

```env
GIGACHAT_CREDENTIALS=<ключ из https://developers.sber.ru/studio/>
```

При проблемах с SSL (например, локально) можно указать: `GIGACHAT_VERIFY_SSL_CERTS=false`.

## Тестирование

```bash
pip install -r requirements.txt
pytest
```

Тесты используют SQLite in-memory, PostgreSQL не требуется.

## Структура проекта

```
carmatch-backend/
├── main.py                    # FastAPI-приложение: CORS, подключение роутеров, лог маршрутов при старте
├── init_db.py                 # Инициализация БД (при необходимости)
├── seed_db.py, seed_db_container.py  # Скрипты заполнения БД (авто, справочники и т.д.)
├── requirements.txt, runtime.txt
├── Dockerfile, docker-compose.yml
├── alembic.ini                # Конфиг Alembic
├── .env.example               # Пример переменных окружения
│
├── src/
│   ├── config.py              # Настройки (pydantic-settings): DATABASE_URL, JWT, CORS, GigaChat, Yandex, GenAPI
│   ├── database.py            # Подключение к БД, sessionmaker, Base; типы JSONBCompat, ArrayTextCompat
│   ├── models.py              # SQLAlchemy-модели: User, Session, ChatMessage, Car, SearchParameter, справочники (CarBrand, CarModel, …)
│   ├── schemas.py             # Pydantic-схемы для запросов/ответов API (auth, chat, cars, admin)
│   ├── deps.py                # Зависимости FastAPI: get_current_user, get_current_admin (JWT + is_admin)
│   │
│   ├── routers/               # Эндпоинты API (все с префиксом /api/v1 в main.py)
│   │   ├── auth.py            # POST /auth/register, /auth/login; GET /auth/me
│   │   ├── chat.py            # POST /chat/complete — свободный чат (GigaChat)
│   │   ├── chat_sessions.py   # Сессии подбора авто: создание, сообщения, поиск по cars (DeepSeek + векторный поиск)
│   │   ├── cars.py            # Публичный поиск автомобилей (по параметрам, векторный поиск)
│   │   ├── admin_cars.py      # CRUD автомобилей (только для is_admin)
│   │   ├── admin_users.py     # Список/профиль/удаление пользователей
│   │   └── admin_sessions.py   # Список/детали/удаление сессий чата
│   │
│   ├── services/              # Бизнес-логика
│   │   ├── auth.py            # Хеширование паролей, JWT, регистрация/логин
│   │   ├── gigachat.py        # Интеграция GigaChat для свободного чата
│   │   ├── deepseek.py        # GenAPI/DeepSeek: классификация сообщений, извлечение параметров, ответы с учётом авто
│   │   ├── chat.py            # Создание сессий, добавление сообщений, оркестрация чата подбора
│   │   ├── vector_search.py   # Векторный и SQL-поиск по cars, гибридный ранжинг
│   │   ├── yandex_embeddings.py # Эмбеддинги (Yandex Foundation Models) для векторного поиска
│   │   ├── yandex_llm.py      # Запросы к Yandex LLM (completion)
│   │   └── reference_data/
│   │       └── car_reference_service.py  # Справочники: бренды, модели, поколения, модификации; поиск по авто
│   │
│   └── utils/
│       ├── car_display.py     # Форматирование авто для отображения
│       ├── modification_parser.py  # Парсинг модификаций
│       └── xml_seeder.py      # Загрузка данных из XML (сиды)
│
├── alembic/
│   ├── env.py                 # Окружение миграций (подключение к БД из config, target_metadata из models)
│   ├── script.py.mako        # Шаблон для новых миграций
│   └── versions/              # Файлы миграций (users, sessions, chat_messages, cars, справочники, админ, эмбеддинги и т.д.)
│
├── tests/
│   ├── conftest.py            # Фикстуры pytest (клиент API, БД in-memory, пользователи)
│   ├── test_auth_api.py       # Тесты регистрации/входа
│   └── test_vector_search.py  # Тесты векторного поиска
│
├── scripts/                   # Вспомогательные скрипты (проверка таблиц, заполнение country/embeddings, Render и т.д.)
│   ├── check_cars_table.py, check_cars_columns.py, check_render_db.py
│   ├── populate_cars_country.py, populate_cars_embeddings.py
│   ├── copy_cars_to_render.py, copy_full_db_to_render.py, update_render_db.py
│   └── vector_search_test.py
│
└── create_reference_tables.sql  # SQL для создания справочных таблиц (при необходимости)
```

Роутеры подключаются в `main.py` с префиксом `/api/v1`. Конфигурация берётся из `.env` (см. `config.py`). Миграции: `alembic upgrade head`.
