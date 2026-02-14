# CarMatch

**CarMatch** — веб-приложение для подбора автомобиля с помощью AI-консультанта. Пользователь общается в чате, указывает предпочтения и бюджет, а система предлагает подходящие варианты. Реализованы регистрация, вход и защищённые маршруты.

---

## Публичная версия

Приложение опубликовано и доступно по адресу:

**https://carmatch-frontend.onrender.com**

Фронтенд развёрнут на Render (static site), бэкенд — отдельный сервис на Render с PostgreSQL.

---

## Структура проекта

```
CarMatch/
├── carmatch-backend/          # Backend (FastAPI, PostgreSQL)
│   ├── src/
│   │   ├── routers/           # API: auth и др.
│   │   ├── services/          # Бизнес-логика
│   │   ├── models.py, schemas.py, database.py
│   │   └── config.py, deps.py
│   ├── alembic/               # Миграции БД
│   ├── tests/
│   ├── main.py
│   ├── Dockerfile
│   └── requirements.txt
│
├── carmatch-frontend/         # Frontend (React, TypeScript, Vite)
│   ├── src/
│   │   ├── api/               # Клиенты API (auth, cars, chat)
│   │   ├── components/        # Chat, CarResults, AuthPage и др.
│   │   ├── contexts/          # AuthContext
│   │   └── pages/
│   ├── Dockerfile
│   └── package.json
│
├── docker-compose.yml         # Локальный запуск: postgres + api
├── render.yaml                # Конфигурация деплоя на Render
└── .github/workflows/ci.yml   # CI (опционально)
```

---

## Как устроен локальный запуск

- **Backend (API + БД)** — запускается в **Docker** из корня репозитория. Uvicorn не запускается вручную: он уже внутри контейнера.
- **Frontend** — запускается **локально** через `npm run dev` в папке `carmatch-frontend`.

Порядок: сначала поднять Docker (бэкенд), затем запустить фронтенд.

---

## Локальный запуск

### 1. Backend и база данных (Docker)

Команды выполнять **в корне репозитория** (папка `CarMatch/`).

**Запустить контейнеры (PostgreSQL + API):**

```bash
docker compose up -d
```

Поднимаются:

- **PostgreSQL** — порт `5432`, БД `carmatch`, пользователь/пароль `carmatch`
- **API** — порт `8000`, при старте выполняются миграции Alembic

**Остановить контейнеры:**

```bash
docker compose down
```

Остановить и удалить тома с данными БД:

```bash
docker compose down -v
```

**Полезные ссылки (при запущенном API):**

- API: http://localhost:8000
- **Swagger (документация API):** http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

Подробнее: [carmatch-backend/README.md](carmatch-backend/README.md).

### 2. Frontend

```bash
cd carmatch-frontend
npm install
npm run dev
```

Приложение будет доступно по адресу **http://localhost:5173** (или порт, который укажет Vite).

Для работы с локальным API создайте в `carmatch-frontend` файл `.env` (по образцу `.env.example`) и при необходимости укажите `VITE_API_BASE_URL=http://localhost:8000`.

---

## Миграции на Render без Shell

На бесплатном плане Render вкладка **Shell** может быть недоступна, а миграции при деплое иногда не срабатывают. Миграции можно выполнить **с вашего компьютера**, подключившись к базе на Render по внешнему URL.

1. **Взять External Database URL на Render**
   - [Dashboard](https://dashboard.render.com) → база **carmatch-db** → вкладка **Info**.
   - Скопировать **External Database URL** (строка вида `postgres://user:password@host/dbname?sslmode=...`).

2. **Запустить миграции локально** (из папки `carmatch-backend`):

   **Windows (cmd):**
   ```cmd
   cd carmatch-backend
   set DATABASE_URL=postgres://...вставьте_скопированный_URL...
   python -m alembic upgrade head
   ```

   **Windows (PowerShell):**
   ```powershell
   cd carmatch-backend
   $env:DATABASE_URL="postgres://...вставьте_скопированный_URL..."
   python -m alembic upgrade head
   ```

   **Linux / macOS:**
   ```bash
   cd carmatch-backend
   export DATABASE_URL="postgres://...вставьте_скопированный_URL..."
   python -m alembic upgrade head
   ```

   Подставлять нужно **полный** URL от Render (с паролем). Префикс `postgres://` или `postgresql://` конфиг бэкенда автоматически приведёт к `postgresql+psycopg://` для драйвера.

3. После успешного выполнения база на Render будет обновлена до последней версии схемы.

---

## Обновление базы на Render

### Вариант 1: Полная копия локальной БД (без cars.xml)

Переносит **все** данные с локальной БД на Render: пользователи, сессии, сообщения, справочники (марки, модели и т.д.) и объявления (`cars`). Файл `cars.xml` не нужен.

**PowerShell** (из папки `carmatch-backend`):
```powershell
cd carmatch-backend
$env:REMOTE_DATABASE_URL="postgresql://user:password@host/dbname?sslmode=require"
python scripts/copy_full_db_to_render.py
```

Скрипт: применяет миграции на Render → очищает таблицы на Render → копирует все строки из локальной БД. Локальная БД по умолчанию: `localhost:5433/carmatch`. Иначе задайте `LOCAL_DATABASE_URL`.

### Вариант 2: Миграции + cars.xml + копия только cars

Если нужны только справочники из XML и объявления с локальной БД:
```powershell
$env:REMOTE_DATABASE_URL="postgresql://..."
python scripts/update_render_db.py
```
(Требуется файл `cars.xml` в корне проекта.)

---

## Стек

- **Backend:** Python, FastAPI, PostgreSQL, Alembic, JWT
- **Frontend:** React 18, TypeScript, Vite, React Router, TanStack Query
- **Инфраструктура:** Docker, Render (деплой)
