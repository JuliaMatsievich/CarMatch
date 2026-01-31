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

## Локальный запуск

### 1. Backend и база данных

В корне репозитория:

```bash
docker compose up -d
```

Поднимаются:

- **PostgreSQL** — порт `5432`, БД `carmatch`, пользователь/пароль `carmatch`
- **API** — порт `8000`, при старте выполняются миграции Alembic

- API: http://localhost:8000
- Документация: http://localhost:8000/docs

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

## Стек

- **Backend:** Python, FastAPI, PostgreSQL, Alembic, JWT
- **Frontend:** React 18, TypeScript, Vite, React Router, TanStack Query
- **Инфраструктура:** Docker, Render (деплой)
