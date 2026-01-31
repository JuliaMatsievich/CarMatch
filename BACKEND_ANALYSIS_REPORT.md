# Отчёт по анализу документации backend-части CarMatch

**Источники:** `CarMatch_Implementation_Spec.md`, `carmatch-frontend/CarMatch_doc.md`  
**Дата:** 31.01.2026  
**Область:** Backend (FastAPI, БД, сервисы, API)

---

## 1. Резюме

Backend CarMatch описан как **FastAPI-приложение** с PostgreSQL, JWT-аутентификацией, чат-сессиями с интеграцией **Ollama (Qwen2.5)** для извлечения параметров из диалога и эндпоинтом поиска автомобилей. Каталог авто для MVP — **статический импорт из Yandex Auto Export (XML)**. Документация содержит однозначные контракты API, DDL таблиц, план реализации (чеклист B1–B15) и критерии приёмки.

---

## 2. Технологический стек (Backend)

| Компонент      | Технология       | Версия / примечание       |
| -------------- | ---------------- | ------------------------- |
| Framework      | FastAPI          | 0.115+                    |
| Язык           | Python           | 3.11+                     |
| ORM            | SQLAlchemy       | 2.0                       |
| Миграции       | Alembic          | 1.x                       |
| БД             | PostgreSQL       | 15+                       |
| AI-инференс    | Ollama + Qwen2.5 | локально или в контейнере |
| Аутентификация | JWT, bcrypt      | —                         |

**Зависимости (из чеклиста B1):** fastapi, uvicorn, sqlalchemy>=2.0, alembic, psycopg2-binary, pydantic, pydantic-settings, python-jose[cryptography], passlib[bcrypt], httpx, python-multipart.

**Ограничения и допущения:**

- Гостевой режим не предусмотрен; обязательная регистрация/авторизация.
- Redis и Celery — опционально для MVP.
- JWT в заголовке `Authorization: Bearer <token>`; refresh-токены — на усмотрение реализации.
- Frontend и Backend развёртываются раздельно (например, Vercel + Render).

---

## 3. Архитектура и компоненты backend

Структура каталога: **carmatch-backend** (в спецификации; в репозитории на момент анализа папки backend нет — учтено в git status).

### 3.1. Таблица компонентов (из раздела 3.2 спецификации)

| Компонент         | Ответственность                                                                  | Файлы/пути                      | Зависимости                                   |
| ----------------- | -------------------------------------------------------------------------------- | ------------------------------- | --------------------------------------------- |
| **auth router**   | POST /register, POST /login; выдача JWT                                          | `src/routers/auth.py`           | FastAPI, schemas, auth service                |
| **auth service**  | Хеш пароля (bcrypt), проверка пароля, создание JWT                               | `src/services/auth.py`          | bcrypt, jwt, database                         |
| **chat router**   | Сессии и сообщения чата (POST/GET)                                               | `src/routers/chat.py`           | get_current_user, chat service, ollama client |
| **chat service**  | Создание сессии, добавление сообщений, вызов Ollama, обновление extracted_params | `src/services/chat.py`          | database, ollama client                       |
| **ollama client** | Запрос к Ollama API, парсинг JSON (response, extracted_params, ready_for_search) | `src/services/ollama_client.py` | httpx, OLLAMA_URL                             |
| **cars router**   | GET /cars/search с query-параметрами                                             | `src/routers/cars.py`           | get_current_user, database                    |
| **models**        | SQLAlchemy: users, cars, sessions, chat_messages, search_parameters              | `src/models.py`                 | SQLAlchemy                                    |
| **schemas**       | Pydantic request/response                                                        | `src/schemas.py`                | Pydantic                                      |
| **database**      | Подключение к PostgreSQL, session factory, get_db()                              | `src/database.py`               | SQLAlchemy, os                                |
| **deps**          | get_current_user: JWT из Authorization, верификация, возврат User или 401        | `src/deps.py` или в auth        | FastAPI Depends, jwt                          |
| **main**          | FastAPI app, CORS, подключение роутеров                                          | `main.py`                       | FastAPI, routers                              |

### 3.2. Поток данных (упрощённо)

- **Регистрация/логин:** Client → POST /api/v1/auth/register|login → auth router → auth service → БД (users) → JWT + user.
- **Чат:** Client → POST /api/v1/chat/sessions → chat router → chat service → БД (sessions).  
  Client → POST .../messages → chat service → БД (chat_messages), Ollama → БД (assistant message, session.extracted_params) → ответ с extracted_params, ready_for_search.
- **Поиск авто:** Client → GET /api/v1/cars/search?… → cars router → БД (cars, фильтры) → { count, results }.

---

## 4. API (контракты)

Базовый URL: `http://localhost:8000/api/v1` (разработка) или `https://api.carmatch.app/v1`. Защищённые эндпоинты: заголовок `Authorization: Bearer <access_token>`.

### 4.1. Авторизация

- **Валидация (общая для register и login):**
  - **email** — обязательное, формат email (Pydantic EmailStr). При ошибке — 422 с detail.
  - **password** — обязательное, минимум 8 символов. При ошибке — 422, например: `"Пароль должен содержать минимум 8 символов"`.
- **Хранение пароля:** только bcrypt-хеш; в ответах и логах пароль не возвращается.

| Метод | Путь                  | Request                   | Успех                               | Ошибки                                       |
| ----- | --------------------- | ------------------------- | ----------------------------------- | -------------------------------------------- |
| POST  | /api/v1/auth/register | `{ "email", "password" }` | 201: access_token, token_type, user | 400 — email занят; 422 — валидация           |
| POST  | /api/v1/auth/login    | то же                     | 200: то же                          | 401 — неверный email/пароль; 422 — валидация |

Формат пользователя в ответе: `id`, `email`, `is_active`, `created_at`.

### 4.2. Чат-сессии

| Метод | Путь                                        | Описание                   | Успех                                                                                              | Ошибки                                                |
| ----- | ------------------------------------------- | -------------------------- | -------------------------------------------------------------------------------------------------- | ----------------------------------------------------- |
| POST  | /api/v1/chat/sessions                       | Создать сессию             | 201: id (uuid), user_id, status, extracted_params, search_results, created_at, updated_at          | —                                                     |
| GET   | /api/v1/chat/sessions                       | Список сессий пользователя | 200: sessions[] (id, status, created_at, updated_at, message_count), по updated_at DESC            | —                                                     |
| POST  | /api/v1/chat/sessions/{session_id}/messages | Отправить сообщение        | 200: id, session_id, role, content, sequence_order, created_at, extracted_params, ready_for_search | 404 — сессия не найдена/не своя; 422 — пустой content |
| GET   | /api/v1/chat/sessions/{session_id}/messages | История сообщений          | 200: messages[] (id, session_id, role, content, sequence_order, created_at)                        | 404                                                   |

После сохранения сообщения пользователя бэкенд вызывает Ollama, сохраняет ответ ассистента и возвращает его вместе с extracted_params и ready_for_search.

### 4.3. Поиск автомобилей

| Метод | Путь                | Query-параметры                                                                      | Успех                     | Ошибки   |
| ----- | ------------------- | ------------------------------------------------------------------------------------ | ------------------------- | -------- |
| GET   | /api/v1/cars/search | budget_max, body_type, min_year, fuel_type, transmission, limit (default 10, max 50) | 200: { count, results[] } | 401, 422 |

Поля результата по машине: id, mark_name, model_name, year, price_rub, body_type, fuel_type, transmission, images, engine_volume, horsepower (и др. по спецификации).

---

## 5. Модель данных

### 5.1. Таблицы и связи (ER)

- **users** — id (SERIAL PK), email (UNIQUE), password_hash, is_active, is_admin, created_at, last_login, login_count. Индексы: email, created_at.
- **sessions** — id (UUID PK), user_id (FK → users, ON DELETE CASCADE), status (active|completed|cancelled|error), extracted_params (JSONB), search_criteria (JSONB), search_results (JSONB), created_at, updated_at, completed_at, message_count, parameters_count, cars_found. Индексы: user_id, status, created_at.
- **chat_messages** — id (BIGSERIAL PK), session_id (FK → sessions, CASCADE), role (user|assistant|system), content (TEXT), metadata (JSONB), sequence_order, created_at. Индексы: session_id, (session_id, sequence_order).
- **search_parameters** — id (BIGSERIAL PK), session_id (FK → sessions, CASCADE), param_type, param_value, confidence (0–1), message_id (FK → chat_messages, SET NULL), created_at. Индекс: session_id.
- **cars** — id (SERIAL PK), source, source_id, mark_name, model_name, body_type, year (CHECK), price_rub (CHECK), fuel_type, engine_volume, horsepower, transmission, specs (JSONB), images (TEXT[]), description, is_active, imported_at, updated_at. Индексы: (mark_name, model_name), year, price_rub, body_type, fuel_type, is_active (partial).

### 5.2. Каскады

- Удаление пользователя → каскадное удаление его сессий (и через FK — сообщений и search_parameters).
- Сессия принадлежит одному пользователю; сообщения и search_parameters — одной сессии.

---

## 6. План реализации backend (Implementation Checklist B1–B15)

| ID  | Задача                    | Краткое содержание                                                                                                                                                                                        |
| --- | ------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| B1  | requirements.txt          | fastapi, uvicorn, sqlalchemy>=2.0, alembic, psycopg2-binary, pydantic, pydantic-settings, python-jose[cryptography], passlib[bcrypt], httpx, python-multipart                                             |
| B2  | database.py               | DATABASE_URL, engine, sessionmaker, get_db()                                                                                                                                                              |
| B3  | models.py                 | SQLAlchemy: User, Session, ChatMessage, Car, SearchParameter по разделу 5 спецификации                                                                                                                    |
| B4  | Alembic                   | Первая миграция: users, sessions, chat_messages, cars, search_parameters; alembic upgrade head                                                                                                            |
| B5  | schemas.py                | Pydantic: RegisterRequest, LoginRequest, AuthResponse, UserResponse, ChatSessionResponse, MessageCreate, MessageResponse, CarSearchResponse, CarResult; валидация email (EmailStr), password min_length=8 |
| B6  | services/auth.py          | hash_password, verify_password, create_access_token, get_user_by_email; регистрация (проверка email) и логин                                                                                              |
| B7  | deps.py                   | get_current_user: Bearer JWT, верификация, загрузка User; при ошибке — 401                                                                                                                                |
| B8  | routers/auth.py           | POST register/login; 201/200 + AuthResponse; 400 при занятом email; 401 при неверном пароле; 422 при валидации                                                                                            |
| B9  | main.py                   | FastAPI, CORS, подключение роутеров auth (далее chat, cars) под /api/v1                                                                                                                                   |
| B10 | services/ollama_client.py | get_ollama_response(messages, system_prompt); POST на OLLAMA_URL (model qwen2.5), парсинг response, extracted_params, ready_for_search; system prompt из CarMatch_doc.md §5.1                             |
| B11 | services/chat.py          | create_session(db, user_id); add_message(...): сохранить user message, вызов Ollama, сохранить assistant message, обновить session.extracted_params и при необходимости search_results                    |
| B12 | routers/chat.py           | POST/GET sessions, POST/GET sessions/{id}/messages; проверка владения сессией                                                                                                                             |
| B13 | routers/cars.py           | GET /cars/search с фильтрами по cars (is_active=true), сортировка (например price_rub ASC), limit 10/50                                                                                                   |
| B14 | main.py                   | Подключить роутеры chat и cars под /api/v1                                                                                                                                                                |
| B15 | Импорт каталога           | Скрипт/команда: парсинг Yandex Auto Export XML → маппинг полей → batch insert в cars. URL: https://auto-export.s3.yandex.net/auto/price-list/catalog/cars.xml или локальный cars.xml                      |

Рекомендуемый порядок: B1–B9 (инфраструктура и авторизация), затем B10–B15 (чат, Ollama, поиск, импорт).

---

## 7. Безопасность и валидация

- **Пароль:** минимум 8 символов (без обязательных требований к сложности для MVP). Валидация в Pydantic и при необходимости в auth service; при нарушении — 422 с явным сообщением в detail.
- **Email:** валидный формат (EmailStr); при нарушении — 422.
- **JWT:** в заголовке `Authorization: Bearer <token>`; проверка на защищённых эндпоинтах; при невалидном/истёкшем токене или отсутствии пользователя — 401 (сообщение типа «Неверный или истёкший токен»).
- **Пароль в БД и логах:** только хеш (bcrypt); в API и логах не возвращается и не выводится.
- В CarMatch_doc.md дополнительно указаны: HTTPS, CORS для trusted domains, rate limiting 60 req/min, защита от SQL injection через ORM.

---

## 8. Внешние интеграции backend

### 8.1. Ollama (Qwen2.5)

- **Назначение:** генерация ответа ассистента и извлечение параметров (extracted_params, ready_for_search) из диалога.
- **Реализация:** POST к OLLAMA_URL (например http://localhost:11434/api/chat), body: model "qwen2.5", messages, stream: false. Парсинг JSON: response, extracted_params, ready_for_search; при отсутствии полей — значения по умолчанию.
- **System prompt:** описан в CarMatch_doc.md §5.1 — русскоязычный AI-консультант CarMatch, сбор параметров (бюджет, тип кузова, год, топливо, КПП), формат вывода JSON с полями response, extracted_params, needs_clarification, ready_for_search. В спецификации в ответе API используется ready_for_search (без needs_clarification в контракте ответа бэкенда).

### 8.2. Yandex Auto Export (каталог автомобилей)

- **Назначение:** наполнение таблицы cars для MVP.
- **Формат:** XML (cars.xml).
- **Задача B15:** скрипт/команда импорта: парсинг XML, маппинг полей в модель cars, batch insert. URL каталога или локальный файл cars.xml.

---

## 9. Соответствие Acceptance Criteria (backend-аспекты)

- Регистрация по email/паролю, выдача JWT; при повторной регистрации с тем же email — 400 «Email уже зарегистрирован».
- Пароль &lt; 8 символов — 422 с текстом про минимум 8 символов.
- Некорректный формат email — 422.
- Логин: при неверных данных — 401 «Неверный email или пароль», без уточнения что именно неверно.
- Без токена доступ к /chat и к API (кроме register/login) невозможен (реализуется через get_current_user и фронт).
- Создание сессии, отправка сообщения, ответ ассистента с задержкой Ollama; в ответе — extracted_params и ready_for_search.
- GET /cars/search с параметрами возвращает { count, results }; каталог заполняется из Yandex Auto Export; поиск только по активным записям cars.

---

## 10. Замечания и пробелы в документации

1. **Структура репозитория:** в спецификации указан каталог `carmatch-backend`; в текущем git status папка backend помечена как удалённая (recovered). Для реализации нужно заново создать структуру backend по чеклисту.
2. **Префикс API:** в тексте указаны и `/api/v1`, и вариант без префикса для базового URL. В реализации следует единообразно использовать префикс `/api/v1` для всех эндпоинтов (как в разделе 4 спецификации).
3. **System prompt:** в CarMatch_doc.md в JSON вывода указано поле `needs_clarification`; в API ответа сообщения в спецификации фигурируют только extracted_params и ready_for_search. Для консистентности имеет смысл либо не отдавать needs_clarification наружу, либо явно добавить его в контракт.
4. **OLLAMA_URL / конфиг:** указано «например http://localhost:11434»; рекомендуется вынести в переменную окружения (например OLLAMA_URL) и описать в .env.example.
5. **Импорт cars (B15):** маппинг полей XML → колонки таблицы cars в спецификации не расписан по полям; его нужно взять из структуры cars.xml и DDL таблицы cars.
6. **Ошибки 500:** формат ответа при внутренних ошибках сервера в документе не описан; ориентир — общепринятая практика FastAPI (detail с сообщением, без раскрытия внутренних деталей).

---

## 11. Выводы

Документация backend-части CarMatch **достаточна для реализации по чеклисту B1–B15**: заданы стек, структура компонентов, контракты API, полные DDL и связи БД, план задач и критерии приёмки. Отчёт можно использовать как единую выжимку по backend при реализации или ревью. Рекомендуется перед стартом восстановить/создать каталог `carmatch-backend` и пройти задачи B1–B9, затем B10–B15.
