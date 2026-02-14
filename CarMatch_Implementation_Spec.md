# CarMatch: Спецификация реализации для кодинг-агентов

Документ предназначен для реализации онлайн-сервиса CarMatch кодинг-агентами (Cursor, Claude, GPT). Каждая секция содержит однозначные контракты и атомарные задачи.

## Структура документа (соответствие чеклисту ревью)

| № | Раздел | Содержание |
|---|--------|------------|
| 1 | Executive Summary | Задача, ограничения, допущения, стек, безопасность |
| 2 | Архитектурные диаграммы | Flowchart системы, sequence-диаграмма, ER-модель |
| 3 | Структура компонентов | Frontend и Backend: ответственность, входы/выходы, файлы, зависимости |
| 4 | API и интерфейсы | Auth, чат-сессии, поиск авто: request/response, коды ошибок, TypeScript-типы |
| 5 | Модель данных | DDL таблиц, связи, каскады, индексы |
| 6 | План реализации | Атомарные задачи Backend (B1–B15) и Frontend (F1–F16) |
| 7 | Acceptance Criteria | Проверяемые критерии приёмки |
| 8 | Риски и альтернативы | Митигации и варианты при изменении требований |
| 9 | Замечания и доп. требования | Практики, справочники, логика чата, промпты |
| — | Ревью архитектора-критика | Вердикт, замечания, рекомендации (см. конец документа) |

---

## 1. Executive Summary

**Задача:** Реализовать веб-сервис CarMatch — AI-консультант по подбору автомобилей с обязательной регистрацией, чат-интерфейсом на русском языке и подбором авто по параметрам, извлечённым из диалога.

**Ключевые ограничения:**
- Обязательная регистрация/авторизация; гостевой режим не предусмотрен.
- Каталог автомобилей для MVP — статический импорт из Yandex Auto Export (XML).
- AI-инференс для MVP — DeepSeek API (модель deepseek-chat) через OpenAI-совместимый клиент.
- Язык интерфейса и диалога — русский.

**Допущения:**
- Frontend и Backend развёртываются раздельно (например, Vercel + Render).
- БД — PostgreSQL (например, Supabase). Redis и Celery — опционально для MVP.
- JWT в заголовке `Authorization: Bearer <token>`; refresh-токены — на усмотрение реализации.

**Безопасность и валидация при регистрации/авторизации:**
- **Пароль:** минимум 8 символов (для MVP без требований к сложности: регистр, цифры, спецсимволы не обязательны). Валидация на бэкенде в Pydantic-схемах и при необходимости в auth service; при нарушении — ответ 422 с полем `detail` (например, `[{ "loc": ["body", "password"], "msg": "Пароль должен содержать минимум 8 символов" }]`).
- **Email:** валидный формат (стандартная валидация, например Pydantic `EmailStr`); при нарушении — 422.
- **Единственный источник токена на фронтенде:** AuthContext. При старте приложения AuthContext инициализирует `token` (и при необходимости `user`) из localStorage (ключ `carmatch_access_token`). Все запросы к API добавляют заголовок `Authorization: Bearer <token>` из текущего значения token в AuthContext; не читать token напрямую из localStorage в API-клиенте.

**Технологический стек:**
| Слой | Технология | Версия |
|------|------------|--------|
| Frontend | React | 18+ |
| Frontend | TypeScript | 5.x |
| Frontend | Vite | 5.x |
| Frontend | React Router | 6.x |
| Frontend | CSS Modules | — |
| Frontend | Axios + TanStack Query (React Query) | актуальные |
| Backend | FastAPI | 0.115+ |
| Backend | Python | 3.11+ |
| Backend | SQLAlchemy | 2.0 |
| Backend | Alembic | 1.x |
| Backend | PostgreSQL | 15+ |
| Backend | DeepSeek API (deepseek-chat) + openai SDK | — |
| Auth | JWT, bcrypt | — |

---

## 2. Архитектурные диаграммы

### 2.1. Общая схема системы (flowchart)

```mermaid
flowchart LR
    subgraph Client["Клиент"]
        Browser[Браузер React SPA]
    end
    subgraph Front["Frontend Host"]
        Vercel[Vercel / Static]
    end
    subgraph Back["Backend"]
        API[FastAPI API]
        DeepSeek[DeepSeek API]
        DB[(PostgreSQL)]
    end
    Browser --> Vercel
    Browser -->|HTTPS/REST| API
    API -->|OpenAI SDK| DeepSeek
    API --> DB
```

### 2.2. Сценарий: регистрация → чат → подбор (sequenceDiagram)

```mermaid
sequenceDiagram
    participant U as User
    participant F as Frontend
    participant A as API
    participant DS as DeepSeek API
    participant D as DB

    U->>F: Открывает сайт
    F->>F: Редирект на /login (если нет token)
    U->>F: Ввод email, пароль, "Зарегистрироваться"
    F->>A: POST /api/v1/auth/register
    A->>D: INSERT user
    A->>F: 201 { access_token, user }
    F->>F: Сохранить token, переход в /chat
    U->>F: Ввод сообщения в чат
    F->>A: GET /api/v1/chat/sessions/current (если нет session_id)
    A->>D: SELECT / INSERT session
    A->>F: 200 { session }
    F->>A: POST /api/v1/chat/sessions/{id}/messages
    A->>D: INSERT chat_message (user)
    A->>DS: Запрос с историей + system prompt (OpenAI SDK)
    DS->>A: JSON { response, extracted_params, ready_for_search }
    A->>D: INSERT chat_message (assistant)
    A->>F: 200 { message, extracted_params, ready_for_search }
    alt ready_for_search && 3+ params
        F->>A: GET /api/v1/cars/search?...
        A->>D: SELECT cars
        A->>F: 200 { results }
        F->>U: Показать карточки авто
    end
```

### 2.3. Модель данных (erDiagram)

```mermaid
erDiagram
    users ||--o{ sessions : "has"
    sessions ||--o{ chat_messages : "contains"
    sessions ||--o{ search_parameters : "extracts"

    users {
        int id PK
        varchar email UK
        varchar password_hash
        bool is_active
        bool is_admin
        timestamp created_at
        timestamp last_login
        int login_count
    }

    sessions {
        uuid id PK
        int user_id FK
        varchar status
        varchar title
        jsonb extracted_params
        jsonb search_criteria
        jsonb search_results
        timestamp created_at
        timestamp updated_at
        timestamp completed_at
        int message_count
        int parameters_count
        int cars_found
    }

    chat_messages {
        bigint id PK
        uuid session_id FK
        varchar role
        text content
        jsonb metadata
        int sequence_order
        timestamp created_at
    }

    car_brands ||--o{ car_models : "has"
    car_models ||--o{ car_generations : "has"
    car_generations ||--o{ car_modifications : "has"
    car_modifications ||--o{ car_complectations : "has"

    car_brands ||--o{ cars : "referenced by"
    car_models ||--o{ cars : "referenced by"
    car_generations ||--o{ cars : "referenced by"
    car_modifications ||--o{ cars : "referenced by"

    car_brands {
        int id PK
        varchar name UK
        varchar code
        timestamp created_at
        timestamp updated_at
    }

    car_models {
        int id PK
        int brand_id FK
        varchar name
        varchar external_id
        timestamp created_at
        timestamp updated_at
    }

    car_generations {
        int id PK
        int model_id FK
        varchar name
        varchar external_id
        jsonb years
        timestamp created_at
        timestamp updated_at
    }

    car_modifications {
        int id PK
        int generation_id FK
        varchar name
        varchar external_id
        varchar body_type
        timestamp created_at
        timestamp updated_at
    }

    car_complectations {
        int id PK
        int modification_id FK
        varchar name
        varchar external_id
        timestamp created_at
        timestamp updated_at
    }

    cars {
        int id PK
        varchar source
        varchar source_id
        varchar mark_name
        varchar model_name
        varchar body_type
        int year
        decimal price_rub
        varchar fuel_type
        decimal engine_volume
        int horsepower
        varchar transmission
        jsonb specs
        text[] images
        text description
        bool is_active
        timestamp imported_at
        timestamp updated_at
        int brand_id FK
        int model_id FK
        int generation_id FK
        int modification_id FK
    }

    search_parameters {
        bigint id PK
        uuid session_id FK
        varchar param_type
        varchar param_value
        decimal confidence
        bigint message_id FK
        timestamp created_at
    }
```

---

## 3. Структура компонентов

### 3.1. Frontend (carmatch-frontend)

| Компонент | Ответственность | Входы | Выходы | Файлы/пути | Зависимости |
|-----------|-----------------|-------|--------|------------|-------------|
| **AuthPage** | Экран входа и регистрации; отправка credentials на API; при успехе — вызов AuthContext.login/register с данными ответа, редирект в /chat | — | Рендер формы, вызов API | `src/pages/AuthPage.tsx`, `src/pages/AuthPage.module.css` | React Router, AuthContext, API client |
| **ProtectedRoute** | Проверка наличия JWT; редирект на /login при отсутствии. Токен берётся только из AuthContext (не из localStorage напрямую) | `children`; внутри использует `token` из AuthContext | Рендер `children` или `<Navigate to="/login" />` | `src/components/ProtectedRoute.tsx` | React Router, AuthContext |
| **ChatLayout** | Область чата: сайдбар с «Новый диалог» и списком сессий, область сообщений, поле ввода | `sessionId`, `sessions`, `messages` | Рендер layout | `src/components/ChatLayout/ChatLayout.tsx`, `ChatLayout.module.css` | React Router, API-клиент |
| **ChatSidebar** | Список сессий пользователя, кнопка «Новый диалог», выход | `sessions[]`, `currentSessionId`, `onNewChat`, `onSelectSession`, `onLogout` | Рендер списка и кнопок | `src/components/ChatLayout/ChatSidebar.tsx` | — |
| **MessageList** | Отображение сообщений user/assistant по порядку `sequence_order` | `messages[]` | Рендер списка сообщений | `src/components/Chat/MessageList.tsx` | — |
| **MessageInput** | Поле ввода и кнопка «Отправить»; вызов API отправки сообщения | `sessionId`, `onSend`, `disabled` | Рендер input + кнопка | `src/components/Chat/MessageInput.tsx` | — |
| **CarResults** | Карточки подобранных автомобилей (марка, модель, год, цена, фото) | `cars[]` из API | Рендер сетки карточек | `src/components/CarResults/CarResults.tsx`, `CarCard.tsx` | — |
| **authApi** | Регистрация, логин; возврат access_token и user. Вызывающий код (AuthPage) передаёт результат в AuthContext.login/register — сохранение token в state и localStorage выполняет только AuthContext | `email`, `password` | Promise<{ access_token, user }> | `src/api/auth.ts` | API client (axios), env VITE_API_BASE_URL |
| **chatApi** | Создание сессии, отправка сообщения, получение истории сообщений | `sessionId?`, `content?` | Promise<session \| message \| messages[]> | `src/api/chat.ts` | API client (токен подставляется интерцептором из AuthContext) |
| **carsApi** | Поиск автомобилей по query-параметрам | `params: { brand?, model?, body_type?, limit? }` | Promise<{ count, results }> | `src/api/cars.ts` | API client |
| **AuthContext** | Единственный источник истины для token и user. При монтировании — восстановление token (и при необходимости user) из localStorage (ключ `carmatch_access_token`). Методы login/register сохраняют переданные access_token и user в state и в localStorage; logout очищает state и localStorage | — | Context: { user, token, login, logout, register } | `src/contexts/AuthContext.tsx` | React |
| **App router** | Маршруты: /login → AuthPage; /chat, /chat/:sessionId? → ProtectedRoute → ChatLayout | — | Router с маршрутами | `src/App.tsx` | React Router |

### 3.2. Backend (carmatch-backend)

| Компонент | Ответственность | Входы | Выходы | Файлы/пути | Зависимости |
|-----------|-----------------|-------|--------|------------|-------------|
| **auth router** | POST /register, POST /login; выдача JWT | Body: email, password | 201/400/422 + access_token, user | `src/routers/auth.py` | FastAPI, schemas, auth service |
| **auth service** | Хеширование пароля (bcrypt), проверка пароля, создание JWT | email, password (plain) | User + token или None | `src/services/auth.py` | bcrypt, jwt, database |
| **chat router** | POST /chat/complete — свободный чат с DeepSeek (без сессий) | JWT, body: messages[] | 200 + content | `src/routers/chat.py` | FastAPI, get_current_user, deepseek service |
| **chat_sessions router** | POST /chat/sessions, GET /chat/sessions, GET /chat/sessions/current, POST /chat/sessions/{id}/messages, GET /chat/sessions/{id}/messages, DELETE /chat/sessions/{id} | JWT, body/path | 201/200/204 + session или message(s) | `src/routers/chat_sessions.py` | FastAPI, get_current_user, chat service |
| **chat service** | Создание сессии, двухшаговая логика добавления сообщения: (1) extract_params через LLM с передачей справочника body_type из БД; (2) поиск в БД если ≥3 параметра, затем generate_response через LLM; сохранение ответа assistant, обновление extracted_params, логирование всех этапов, автоназвание сессии | user_id, session_id, content | Session, Message | `src/services/chat.py` | database, deepseek service, car reference service |
| **deepseek service** | Два LLM-запроса: (1) extract_params — извлечение параметров (brand, model, body_type) из истории с передачей справочника body_type из БД; (2) generate_response — генерация текста ответа пользователю по собранным параметрам и результатам поиска | messages[], params, body_type_reference, search_results | dict с extracted_params; str с текстом ответа | `src/services/deepseek.py` | openai SDK, DEEPSEEK_API_KEY |
| **cars router** | GET /cars/search с query-параметрами из справочников; фильтрация по БД через `brand_id`, `model_id`, `body_type` | Query: brand, model, body_type, limit | 200 { count, results } | `src/routers/cars.py` | FastAPI, get_current_user, database, car_brands, car_models |
| **users/cars/sessions/models** | SQLAlchemy модели для users, cars, sessions, chat_messages, search_parameters | — | — | `src/models.py` | SQLAlchemy |
| **schemas** | Pydantic-модели для request/response | — | — | `src/schemas.py` | Pydantic |
| **database** | Подключение к PostgreSQL, session factory | DATABASE_URL | Session | `src/database.py` | SQLAlchemy, os |
| **middleware/deps** | get_current_user: извлечение JWT из Authorization, проверка, возврат User | Header Authorization | User или 401 | `src/deps.py` или в `auth.py` | FastAPI Depends, jwt |
| **main** | Сборка FastAPI app, подключение роутеров, CORS | — | FastAPI app | `main.py` | FastAPI, routers |

---

## 4. API и интерфейсы

Базовый URL API: `https://api.carmatch.app/v1` или для разработки: `http://localhost:8000/api/v1`. Все защищённые эндпоинты требуют заголовок: `Authorization: Bearer <access_token>`.

### 4.1. Авторизация

**Валидация входных данных (общая для register и login):**
- **email** — обязательное поле, формат email (например, Pydantic `EmailStr`). При нарушении — 422, в `detail` указать причину (например, `"Некорректный формат email"`).
- **password** — обязательное поле, минимум 8 символов. При нарушении — 422, в `detail` указать (например, `"Пароль должен содержать минимум 8 символов"`).

**Хранение пароля на бэкенде:** только хеш (bcrypt с солью). В ответах API и в логах пароль никогда не возвращается и не выводится.

#### POST /api/v1/auth/register

**Request:**
```json
{
  "email": "user@example.com",
  "password": "securepassword123"
}
```

**Response 201:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "email": "user@example.com",
    "is_active": true,
    "created_at": "2026-01-27T12:00:00Z"
  }
}
```

**Коды ошибок:**
- **400** — email уже зарегистрирован. Тело ответа: `{ "detail": "Email уже зарегистрирован" }` (или аналогичное сообщение).
- **422** — ошибка валидации (некорректный формат email, пароль короче 8 символов). Тело: массив ошибок в формате FastAPI, например `[{ "loc": ["body", "password"], "msg": "Пароль должен содержать минимум 8 символов", "type": "value_error" }]`.

**TypeScript (frontend):**
```ts
interface RegisterRequest {
  email: string;
  password: string;
}
interface AuthUser {
  id: number;
  email: string;
  is_active: boolean;
  created_at: string;
}
interface AuthResponse {
  access_token: string;
  token_type: string;
  user: AuthUser;
}
```

---

#### POST /api/v1/auth/login

**Request:** тот же что и register (email, password). Валидация формата email и длины пароля — как для register.

**Response 200:** тот же формат что и AuthResponse выше.

**Коды ошибок:**
- **401** — неверный email или пароль. Тело ответа: `{ "detail": "Неверный email или пароль" }`. Не раскрывать, что именно неверно (email или пароль).
- **422** — ошибка валидации (формат email, длина пароля); формат `detail` — как для register.

---

### 4.2. Чат-сессии

#### POST /api/v1/chat/sessions

**Request:** тело пустое или `{}`. Заголовок: `Authorization: Bearer <token>`.

**Response 201:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "user_id": 1,
  "status": "active",
  "extracted_params": {},
  "search_results": [],
  "created_at": "2026-01-27T12:00:00Z",
  "updated_at": "2026-01-27T12:00:00Z"
}
```

**TypeScript:**
```ts
interface ChatSession {
  id: string;
  user_id: number;
  status: 'active' | 'completed' | 'cancelled' | 'error';
  extracted_params: Record<string, unknown>;
  search_results: unknown[];
  created_at: string;
  updated_at: string;
}
```

---

#### GET /api/v1/chat/sessions

**Response 200:**
```json
{
  "sessions": [
    {
      "id": "uuid",
      "status": "active",
      "created_at": "...",
      "updated_at": "...",
      "message_count": 5
    }
  ]
}
```

Список только сессий текущего пользователя, упорядоченный по `updated_at` DESC. Каждый элемент включает поле `title` — автоматически формируемый заголовок из первого сообщения пользователя (до 60 символов).

**TypeScript (элемент списка):**
```ts
interface ChatSessionListItem {
  id: string;
  status: string;
  title?: string | null;
  created_at: string;
  updated_at: string;
  message_count: number;
}
```

---

#### GET /api/v1/chat/sessions/current

Возвращает «текущий новый диалог» — последнюю пустую сессию пользователя (message_count = 0). Если пустых сессий нет — создаёт новую. Используется фронтендом при открытии /chat без sessionId для автоматического перехода в актуальную сессию.

**Response 200:** тот же формат что и ChatSessionResponse.

---

#### DELETE /api/v1/chat/sessions/{session_id}

Удаляет сессию текущего пользователя. Сообщения и search_parameters удаляются каскадно.

**Response 204:** тело пустое.

**Коды ошибок:** 404 (сессия не найдена или не принадлежит пользователю), 401 (нет токена).

---

#### POST /api/v1/chat/sessions/{session_id}/messages

**Request:**
```json
{
  "content": "Хочу Toyota, внедорожник"
}
```

**Response 200:**
```json
{
  "id": 123,
  "session_id": "uuid",
  "role": "assistant",
  "content": "Отлично, Toyota — хороший выбор! Какую модель рассматриваете?",
  "sequence_order": 2,
  "created_at": "...",
  "extracted_params": [
    { "type": "brand", "value": "Toyota", "confidence": 0.95 },
    { "type": "body_type", "value": "внедорожник 5 дв.", "confidence": 0.9 }
  ],
  "ready_for_search": false
}
```

После сохранения сообщения пользователя бэкенд вызывает DeepSeek API, сохраняет ответ assistant и возвращает его вместе с извлечёнными параметрами и флагом `ready_for_search`. Если `ready_for_search === true` и параметров достаточно (≥3), фронтенд вызывает GET /cars/search.

**Коды ошибок:** 404 (сессия не найдена или не принадлежит пользователю), 422 (пустой content).

**TypeScript:**
```ts
interface SendMessageRequest {
  content: string;
}
interface ExtractedParam {
  type: string;
  value: string;
  confidence: number;
}
interface SendMessageResponse {
  id: number;
  session_id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  sequence_order: number;
  created_at: string;
  extracted_params?: ExtractedParam[];
  ready_for_search?: boolean;
}
```

---

#### GET /api/v1/chat/sessions/{session_id}/messages

**Response 200:**
```json
{
  "messages": [
    {
      "id": 1,
      "session_id": "uuid",
      "role": "user",
      "content": "Нужна машина для города",
      "sequence_order": 1,
      "created_at": "..."
    },
    {
      "id": 2,
      "session_id": "uuid",
      "role": "assistant",
      "content": "Понял! Какой бюджет?",
      "sequence_order": 2,
      "created_at": "..."
    }
  ]
}
```

---

### 4.3. Свободный чат (без сессий)

#### POST /api/v1/chat/complete

Отправляет историю сообщений в DeepSeek и возвращает ответ ассистента. Свободный режим без привязки к сессиям и БД автомобилей.

**Request:**
```json
{
  "messages": [
    { "role": "user", "content": "Привет! Расскажи про электромобили" }
  ]
}
```

**Response 200:**
```json
{
  "content": "Электромобили — это транспортные средства с электродвигателем..."
}
```

**Коды ошибок:** 401 (нет токена), 502 (ошибка DeepSeek API), 503 (DEEPSEEK_API_KEY не задан).

**TypeScript:**
```ts
interface ChatCompleteMessage {
  role: 'user' | 'assistant';
  content: string;
}
interface ChatCompleteRequest {
  messages: ChatCompleteMessage[];
}
interface ChatCompleteResponse {
  content: string;
}
```

---

### 4.4. Поиск автомобилей

#### GET /api/v1/cars/search

Поиск ведётся по параметрам из справочников БД (см. раздел 9.3). Тип кузова — по точному значению из справочника `car_modifications.body_type`; марка и модель — текстовым поиском через справочники `car_brands` и `car_models` с получением `brand_id` / `model_id`.

**Query-параметры:**

| Параметр | Тип | Обязательный | Описание | Способ поиска |
|----------|-----|--------------|----------|---------------|
| brand | string | нет | Марка (Toyota, BMW, Lada…) | Текстовый поиск по `car_brands.name` → `cars.brand_id` |
| model | string | нет | Модель (Camry, X5, Vesta…) | Текстовый поиск по `car_models.name` → `cars.model_id` |
| body_type | string | нет | Тип кузова (седан, внедорожник, хэтчбек…) | Точное значение из справочника `car_modifications.body_type` |
| limit | number | нет | Макс. количество (по умолчанию 10, макс. 50) | — |

**Response 200:**
```json
{
  "count": 3,
  "results": [
    {
      "id": 1,
      "mark_name": "Toyota",
      "model_name": "RAV4",
      "year": 2022,
      "body_type": "внедорожник 5 дв.",
      "brand_id": 42,
      "model_id": 318,
      "generation_id": 1205,
      "modification_id": 5410,
      "images": [],
      "engine_volume": 2.5,
      "horsepower": 199
    }
  ]
}
```

**TypeScript:**
```ts
interface CarSearchParams {
  brand?: string;
  model?: string;
  body_type?: string;
  limit?: number;
}
interface CarResult {
  id: number;
  mark_name: string;
  model_name: string;
  year: number | null;
  price_rub: number | null;
  body_type: string | null;
  fuel_type: string | null;
  transmission: string | null;
  images: string[];
  engine_volume?: number;
  horsepower?: number;
  brand_id?: number;
  model_id?: number;
  generation_id?: number;
  modification_id?: number;
}
interface CarSearchResponse {
  count: number;
  results: CarResult[];
}
```

**Коды ошибок:** 401 (нет токена), 422 (некорректные параметры).

---

### 4.5. Примеры запросов (curl)

```bash
# Регистрация
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"securepassword123"}'

# Создание сессии (подставить TOKEN)
curl -X POST http://localhost:8000/api/v1/chat/sessions \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json"

# Отправка сообщения (подставить SESSION_ID и TOKEN)
curl -X POST "http://localhost:8000/api/v1/chat/sessions/SESSION_ID/messages" \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"content":"Машина для города до 2 млн"}'

# Поиск авто (по справочным параметрам)
curl "http://localhost:8000/api/v1/cars/search?brand=Toyota&body_type=внедорожник+5+дв.&limit=5" \
  -H "Authorization: Bearer TOKEN"
```

---

## 5. Модель данных

### 5.1. Таблицы (полные DDL)

Исходное ТЗ: `carmatch-frontend/CarMatch_doc.md`, раздел 3. Ниже — сводка и полные DDL для всех таблиц.

**users**
```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT true,
    is_admin BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT NOW(),
    last_login TIMESTAMP,
    login_count INTEGER DEFAULT 0
);
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_created_at ON users(created_at);
```

**sessions**
```sql
CREATE TABLE sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'completed', 'cancelled', 'error')),
    title VARCHAR(200),
    extracted_params JSONB DEFAULT '{}',
    search_criteria JSONB DEFAULT '{}',
    search_results JSONB DEFAULT '[]',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP,
    message_count INTEGER DEFAULT 0,
    parameters_count INTEGER DEFAULT 0,
    cars_found INTEGER DEFAULT 0
);
CREATE INDEX idx_sessions_user_id ON sessions(user_id);
CREATE INDEX idx_sessions_status ON sessions(status);
CREATE INDEX idx_sessions_created_at ON sessions(created_at);
```

**chat_messages**
```sql
CREATE TABLE chat_messages (
    id BIGSERIAL PRIMARY KEY,
    session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    metadata JSONB DEFAULT '{}',
    sequence_order INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX idx_chat_messages_session_id ON chat_messages(session_id);
CREATE INDEX idx_chat_messages_sequence ON chat_messages(session_id, sequence_order);
```

**search_parameters**
```sql
CREATE TABLE search_parameters (
    id BIGSERIAL PRIMARY KEY,
    session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    param_type VARCHAR(50) NOT NULL,
    param_value VARCHAR(255),
    confidence DECIMAL(3,2) CHECK (confidence >= 0 AND confidence <= 1),
    message_id BIGINT REFERENCES chat_messages(id) ON DELETE SET NULL,
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX idx_search_parameters_session_id ON search_parameters(session_id);
```

**cars**
```sql
CREATE TABLE cars (
    id SERIAL PRIMARY KEY,
    source VARCHAR(20) NOT NULL DEFAULT 'yandex',
    source_id VARCHAR(100),
    mark_name VARCHAR(100) NOT NULL,
    model_name VARCHAR(100) NOT NULL,
    body_type VARCHAR(50),
    year INTEGER,
    price_rub DECIMAL(12,2),
    fuel_type VARCHAR(30),
    engine_volume DECIMAL(4,2),
    horsepower INTEGER,
    transmission VARCHAR(30),
    specs JSONB NOT NULL DEFAULT '{}'::jsonb,
    images TEXT[],
    description TEXT,
    is_active BOOLEAN NOT NULL DEFAULT true,
    imported_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    brand_id INTEGER REFERENCES car_brands(id) ON DELETE SET NULL,
    model_id INTEGER REFERENCES car_models(id) ON DELETE SET NULL,
    generation_id INTEGER REFERENCES car_generations(id) ON DELETE SET NULL,
    modification_id INTEGER REFERENCES car_modifications(id) ON DELETE SET NULL
);
CREATE INDEX idx_cars_mark_model ON cars(mark_name, model_name);
CREATE INDEX idx_cars_year ON cars(year);
CREATE INDEX idx_cars_price ON cars(price_rub);
CREATE INDEX idx_cars_body_type ON cars(body_type);
CREATE INDEX idx_cars_fuel_type ON cars(fuel_type);
CREATE INDEX idx_cars_is_active ON cars(is_active) WHERE is_active = true;
CREATE INDEX idx_cars_brand ON cars(brand_id);
CREATE INDEX idx_cars_model ON cars(model_id);
CREATE INDEX idx_cars_generation ON cars(generation_id);
CREATE INDEX idx_cars_modification ON cars(modification_id);
```

**car_brands**
```sql
CREATE TABLE car_brands (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    code VARCHAR(50),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);
CREATE INDEX ix_car_brands_id ON car_brands(id);
CREATE INDEX idx_car_brands_name ON car_brands(name);
```

**car_models**
```sql
CREATE TABLE car_models (
    id SERIAL PRIMARY KEY,
    brand_id INTEGER NOT NULL REFERENCES car_brands(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    external_id VARCHAR(100),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);
CREATE INDEX ix_car_models_id ON car_models(id);
CREATE INDEX idx_car_models_brand ON car_models(brand_id);
CREATE INDEX idx_car_models_name ON car_models(name);
CREATE INDEX idx_car_models_external_id ON car_models(external_id);
```

**car_generations**
```sql
CREATE TABLE car_generations (
    id SERIAL PRIMARY KEY,
    model_id INTEGER NOT NULL REFERENCES car_models(id) ON DELETE CASCADE,
    name VARCHAR(100),
    external_id VARCHAR(100),
    years JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);
CREATE INDEX ix_car_generations_id ON car_generations(id);
CREATE INDEX idx_car_generations_model ON car_generations(model_id);
CREATE INDEX idx_car_generations_external_id ON car_generations(external_id);
```

**car_modifications**
```sql
CREATE TABLE car_modifications (
    id SERIAL PRIMARY KEY,
    generation_id INTEGER NOT NULL REFERENCES car_generations(id) ON DELETE CASCADE,
    name VARCHAR(200) NOT NULL,
    external_id VARCHAR(100),
    body_type VARCHAR(100),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);
CREATE INDEX ix_car_modifications_id ON car_modifications(id);
CREATE INDEX idx_car_modifications_generation ON car_modifications(generation_id);
CREATE INDEX idx_car_modifications_external_id ON car_modifications(external_id);
```

**car_complectations**
```sql
CREATE TABLE car_complectations (
    id SERIAL PRIMARY KEY,
    modification_id INTEGER NOT NULL REFERENCES car_modifications(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    external_id VARCHAR(100),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);
CREATE INDEX ix_car_complectations_id ON car_complectations(id);
CREATE INDEX idx_car_complectations_modification ON car_complectations(modification_id);
CREATE INDEX idx_car_complectations_external_id ON car_complectations(external_id);
```

### 5.2. Связи и каскады

- Удаление пользователя → каскадное удаление его сессий (и при необходимости сообщений и search_parameters, если не задано иначе через FK).
- Сессия принадлежит одному пользователю. Сообщения и search_parameters принадлежат одной сессии.

---

## 6. План реализации (Implementation Checklist)

Задачи сгруппированы так, чтобы агент мог выполнять их по одной. Порядок соблюдать по зависимостям.

### Backend

- [ ] **B1.** Создать `carmatch-backend/requirements.txt` с зависимостями: fastapi, uvicorn[standard], sqlalchemy>=2.0, alembic, psycopg[binary]>=3.1 (драйвер psycopg3), pydantic[email], pydantic-settings, email-validator, python-jose[cryptography], bcrypt, python-multipart, openai>=1.0.0 (для DeepSeek API), pytest, httpx.
- [ ] **B2.** Создать `carmatch-backend/src/database.py`: подключение к PostgreSQL по переменной окружения DATABASE_URL, создание engine и sessionmaker (SessionLocal), контекстный менеджер get_db().
- [ ] **B3.** Создать `carmatch-backend/src/models.py`: модели SQLAlchemy для User, Session, ChatMessage, Car, SearchParameter с полями и связями по разделу 5.
- [ ] **B4.** Создать первую миграцию Alembic: добавление таблиц users, sessions, chat_messages, cars, search_parameters. Команда: `alembic revision --autogenerate -m "initial"`, затем `alembic upgrade head`.
- [ ] **B5.** Создать `carmatch-backend/src/schemas.py`: Pydantic-модели для RegisterRequest, LoginRequest, AuthResponse, UserResponse, ChatSessionResponse, MessageCreate, MessageResponse, CarSearchResponse, CarResult; при необходимости — для списков (sessions list, messages list). Для RegisterRequest и LoginRequest задать валидацию: email — EmailStr (или аналог с форматом email); password — min_length=8 (сообщение об ошибке: «Пароль должен содержать минимум 8 символов»).
- [ ] **B6.** Создать `carmatch-backend/src/services/auth.py`: функции hash_password(password) — bcrypt с солью, verify_password(plain, hashed), create_access_token(user_id, email), get_user_by_email(db, email); регистрация (проверка существования email — при наличии возвращать None или флаг «email занят»; создание User с хешем пароля, возврат token и user); логин (проверка пароля через verify_password — при неверном пароле возвращать None; при успехе — token и user).
- [ ] **B7.** Создать `carmatch-backend/src/deps.py`: зависимость get_current_user(credentials: HTTPAuthorizationCredentials, db: Session) — извлечение JWT из Bearer, верификация подписи и срока действия, загрузка User из БД по id из payload; при отсутствии/невалидном токене или несуществующем пользователе — HTTPException 401 с сообщением «Неверный или истёкший токен» (или аналог).
- [ ] **B8.** Создать `carmatch-backend/src/routers/auth.py`: POST /api/v1/auth/register и POST /api/v1/auth/login; вызов auth service; при регистрации: если email уже занят — 400 с detail «Email уже зарегистрирован»; при нарушении валидации Pydantic — 422 с detail из FastAPI; при успехе — 201 и AuthResponse. При логине: при неверном email или пароле — 401 с detail «Неверный email или пароль»; при 422 — как для register; при успехе — 200 и AuthResponse.
- [ ] **B9.** Создать `carmatch-backend/main.py`: экземпляр FastAPI, CORS middleware (разрешить origin фронтенда), подключение роутеров auth и (ниже) chat, cars; точка входа uvicorn.
- [ ] **B10.** Создать `carmatch-backend/src/services/deepseek.py`: OpenAI-совместимый клиент для DeepSeek API (base_url=https://api.deepseek.com, model=deepseek-chat). Функции: (a) `chat_complete(messages)` — свободный чат; (b) `extract_params(messages, current_params, body_type_reference)` — Шаг 1: извлечение параметров подбора (brand, model, body_type) из истории диалога, с передачей справочника body_type из БД; (c) `generate_response(messages, params, search_results)` — Шаг 2: генерация текстового ответа пользователю на основе собранных параметров и результатов поиска. DEEPSEEK_API_KEY берётся из env через Settings. Промпты — в константах модуля.
- [ ] **B11.** Создать `carmatch-backend/src/services/chat.py`: create_session(db, user_id) → Session; add_message(db, session_id, user_id, content) — двухшаговая логика: (Шаг 1) сохранить user message, при первом сообщении задать session.title, вызвать deepseek.extract_params с историей и справочником body_type из БД → получить параметры (brand, model, body_type); (Шаг 2) если ≥3 параметра — выполнить поиск в БД, затем вызвать deepseek.generate_response с параметрами и результатами поиска; если <3 — вызвать deepseek.generate_response с просьбой задать уточняющие вопросы. Сохранить assistant message, обновить session.extracted_params, записать search_parameters. Логировать все этапы в metadata сообщений.
- [ ] **B12a.** Создать `carmatch-backend/src/routers/chat.py`: POST /api/v1/chat/complete — свободный чат с DeepSeek (без сессий и БД машин); вызов deepseek.chat_complete.
- [ ] **B12b.** Создать `carmatch-backend/src/routers/chat_sessions.py`: POST /api/v1/chat/sessions, GET /api/v1/chat/sessions, GET /api/v1/chat/sessions/current, POST /api/v1/chat/sessions/{session_id}/messages, GET /api/v1/chat/sessions/{session_id}/messages, DELETE /api/v1/chat/sessions/{session_id}; проверка владения сессией пользователем.
- [ ] **B13.** Создать `carmatch-backend/src/routers/cars.py`: GET /api/v1/cars/search с query-параметрами brand, model, body_type, limit; поиск марки и модели — текстовый через справочники car_brands и car_models → получение brand_id / model_id → фильтрация cars; тип кузова — по точному значению из справочника car_modifications.body_type; только is_active=true; limit по умолчанию 10, макс. 50; ответ в формате { count, results }.
- [ ] **B14.** Подключить роутеры auth, chat, chat_sessions и cars в main.py под префиксом /api/v1.
- [ ] **B15.** Реализовать скрипт или команду импорта каталога из Yandex Auto Export XML в таблицу cars (парсинг XML, маппинг полей, batch insert). URL XML: https://auto-export.s3.yandex.net/auto/price-list/catalog/cars.xml (или локальный файл cars.xml).

### Frontend

- [ ] **F1.** Убедиться, что в проекте есть зависимости: react, react-dom, react-router-dom, axios, @tanstack/react-query, typescript, vite. Добавить при необходимости в package.json и установить.
- [ ] **F2.** Создать `src/api/client.ts`: экземпляр axios с baseURL из import.meta.env.VITE_API_BASE_URL; интерцептор request — добавлять заголовок `Authorization: Bearer <token>`, где token берётся **только из AuthContext** (единственный источник). Поскольку client.ts не имеет доступа к React-контексту напрямую, реализовать одним из способов: (a) передавать в client функцию getToken() при создании (например, из AuthContext при инициализации приложения), либо (b) экспортировать из client метод setAuthToken(token) и вызывать его из AuthContext при login/register/logout, храня токен также в замыкании или переменной модуля client. Не читать token напрямую из localStorage в client.
- [ ] **F3.** Создать `src/api/auth.ts`: функции register(email, password), login(email, password); вызов POST /api/v1/auth/register и POST /api/v1/auth/login через client; возврат данных ответа (access_token, user). Вызывающий код (AuthPage) после успешного ответа передаёт access_token и user в AuthContext.login или AuthContext.register — сохранение в state и localStorage выполняет только AuthContext.
- [ ] **F4.** Создать `src/api/chat.ts`: createSession(), getSessions(), getMessages(sessionId), sendMessage(sessionId, content); все запросы через client с токеном.
- [ ] **F5.** Создать `src/api/cars.ts`: searchCars(params: CarSearchParams); GET /api/v1/cars/search с query-параметрами.
- [ ] **F6.** Создать `src/contexts/AuthContext.tsx`: единственный источник истины для token и user. При монтировании провайдера — восстановление token из localStorage (ключ `carmatch_access_token`); при необходимости восстанавливать user из localStorage (ключ `carmatch_user`) или загружать по токену. Методы login(access_token, user), register(access_token, user) сохраняют переданные данные в state и в localStorage; logout очищает state и localStorage (и при использовании F2(b) — сбрасывает токен в client). Провайдер оборачивает приложение (например, корень Router).
- [ ] **F7.** Создать `src/components/ProtectedRoute.tsx`: читать token только из AuthContext (useContext(AuthContext).token); при отсутствии token — <Navigate to="/login" replace />, иначе — <Outlet /> или children.
- [ ] **F8.** Создать `src/pages/AuthPage.tsx`: форма с полями email и password; кнопки «Войти» и «Зарегистрироваться»; вызов authApi.login/register, при успехе — вызов AuthContext.login или AuthContext.register с access_token и user из ответа (AuthContext сам сохраняет в state и localStorage); затем редирект на /chat. Стили в AuthPage.module.css. Опционально: клиентская валидация пароля (минимум 8 символов) и формата email перед отправкой.
- [ ] **F9.** Создать `src/pages/ChatPage.tsx`: при открытии /chat без sessionId — получить текущую пустую сессию через GET /chat/sessions/current (или создать новую) и редирект на /chat/:sessionId; при наличии sessionId — загрузка сообщений getMessages(sessionId), рендер ChatLayout с MessageList и MessageInput.
- [ ] **F10.** Создать `src/components/ChatLayout/ChatLayout.tsx` и `ChatLayout.module.css`: сайдбар слева (список сессий + «Новый диалог» + «Выйти»), справа — область сообщений и поле ввода; пропсы: sessionId, sessions, messages, onNewChat, onSelectSession, onSend, onLogout.
- [ ] **F11.** Создать `src/components/Chat/MessageList.tsx`: отображение сообщений по sequence_order; различие стилей для role user и assistant.
- [ ] **F12.** Создать `src/components/Chat/MessageInput.tsx`: контролируемый input и кнопка «Отправить»; при отправке вызвать onSend(content), затем обновить список сообщений (через refetch или передачу нового сообщения в state).
- [ ] **F13.** В ChatPage: при ответе sendMessage с ready_for_search === true и достаточным количеством extracted_params вызвать searchCars(extracted_params) и отобразить блок CarResults под сообщениями.
- [ ] **F14.** Создать `src/components/CarResults/CarResults.tsx` и `CarCard.tsx`: сетка карточек; каждая карточка: mark_name, model_name, year, price_rub, при наличии — первое изображение из images; стили в CSS Modules.
- [ ] **F15.** Настроить маршруты в App.tsx: /login → AuthPage; /chat и /chat/:sessionId обёрнуты в ProtectedRoute, рендер ChatPage; по умолчанию редирект с / на /chat или /login в зависимости от токена.
- [ ] **F16.** Добавить в .env.example переменную VITE_API_BASE_URL=http://localhost:8000 (или URL бэкенда).

---

## 7. Acceptance Criteria

- ✅ Пользователь может зарегистрироваться по email и паролю и получить JWT; при повторной регистрации с тем же email возвращается 400 с сообщением «Email уже зарегистрирован».
- ✅ При регистрации с паролем короче 8 символов API возвращает 422 с описанием ошибки валидации (например, «Пароль должен содержать минимум 8 символов»).
- ✅ При регистрации или входе с некорректным форматом email API возвращает 422 с описанием ошибки.
- ✅ Пользователь может войти по email и паролю и получить JWT; при неверных данных возвращается 401 с сообщением «Неверный email или пароль» (без раскрытия, что именно неверно).
- ✅ Без токена доступ к /chat и к API (кроме register/login) невозможен; фронтенд берёт токен из AuthContext и перенаправляет на /login при отсутствии токена.
- ✅ После входа пользователь попадает в чат; при первом заходе создаётся новая сессия и отображается пустой список сообщений.
- ✅ Пользователь вводит сообщение и нажимает «Отправить»; сообщение отображается в чате; ответ ассистента появляется после ответа API (с задержкой вызова DeepSeek).
- ✅ В ответе API сообщения присутствуют поля extracted_params и ready_for_search; при ready_for_search и достаточном числе параметров фронтенд показывает блок с результатами поиска автомобилей.
- ✅ GET /cars/search с параметрами (brand, model, body_type) возвращает список автомобилей из БД в формате { count, results }; поиск ведётся через справочники (car_brands, car_models, car_modifications); результаты отображаются в виде карточек со всеми известными характеристиками.
- ✅ В сайдбаре отображается список сессий пользователя; можно создать «Новый диалог» и переключаться между сессиями; при выборе сессии подгружаются её сообщения.
- ✅ Пользователь может выйти (logout); AuthContext очищает token и user из state и из localStorage; при использовании F2(b) токен сбрасывается и в API-клиенте; происходит редирект на /login.
- ✅ Каталог автомобилей заполняется из Yandex Auto Export (или локального XML); поиск по фильтрам возвращает только активные записи cars.

---

## 8. Риски и альтернативы

| Риск | Митигация |
|------|-----------|
| Ограничения бесплатного хостинга (Render/Vercel/Supabase) | Мониторить лимиты; при достижении лимитов рассмотреть платный tier или перенос на другой провайдер. |
| Долгий ответ DeepSeek API (>4 сек) | Кэшировать типовые ответы; сократить длину контекста; в UI показывать индикатор загрузки. |
| Нестабильный формат JSON от LLM | Парсить ответ с fallback: при ошибке считать ready_for_search=false, extracted_params=[]; логировать сырой ответ для доработки промпта. |
| Недоступность DeepSeek API | При ошибке от API возвращать пользователю сообщение «Не удалось обработать запрос. Попробуйте ещё раз.»; логировать ошибку. |
| Нехватка данных в Yandex XML | Документировать маппинг полей; при отсутствии полей оставлять NULL; в будущем подключить Auto.dev API. |

**Альтернативы при изменении требований:**

- Замена DeepSeek на другой LLM (OpenAI, Yandex GPT и др.): благодаря использованию OpenAI-совместимого SDK достаточно изменить `base_url` и `model` в `deepseek.py`; для кардинально другого API — вынести вызов в отдельный адаптер с единым интерфейсом.
- WebSocket вместо REST для чата: добавить эндпоинт WebSocket /ws/chat/{session_id}; фронтенд подключается к нему и отправляет сообщения через сокет; ответ ассистента приходит стримом или одним сообщением; текущий REST можно оставить для совместимости или удалить после миграции.
- Гостевой режим: ввести анонимные сессии (user_id nullable или отдельная таблица guest_sessions); выдавать временный JWT или session_id без привязки к user; ограничить функционал для гостя (например, только один диалог).

---

## 9. Замечания и дополнительные требования

Ниже — замечания и уточнения к реализации (к выполнению при последующих итерациях).

### 9.1. Общие практики

- Использовать лучшие практики и подходы при разработке масштабируемых приложений на соответствующих фреймворках (FastAPI, React и др.).

### 9.2. Справочник автомобилей и БД

- В файле **cars.xml** в корне проекта лежит база-справочник автомобилей.
- На её основе необходимо спроектировать **нормализованную БД** и затем в виде **сидера** прогнать все эти справочники в неё.

### 9.3. Принцип работы чата (логика бэкенда)

Пользователь пишет сообщение — оно отправляется на бэкенд.

**Важно:** пока всё взаимодействие должно быть **синхронным**, без фоновых задач и очередей — для простоты отладки. При этом все ключевые этапы логики необходимо **инкапсулировать в отдельные функции**, чтобы в дальнейшем их можно было использовать для реализации асинхронного варианта.

**Справочники, имеющиеся в БД (источник параметров для поиска):**

| Таблица | Ключевые поля | Что содержит |
|---------|---------------|--------------|
| `car_brands` | `id`, `name`, `code` | Марки автомобилей (Toyota, BMW, Lada…) |
| `car_models` | `id`, `brand_id`, `name` | Модели (Camry, X5, Vesta…) |
| `car_generations` | `id`, `model_id`, `name`, `years` (JSONB) | Поколения с диапазоном годов |
| `car_modifications` | `id`, `generation_id`, `name`, `body_type` | Модификации с типом кузова |
| `car_complectations` | `id`, `modification_id`, `name` | Комплектации |

**Параметры подбора, извлекаемые из диалога:**

| Параметр | Источник в БД | Способ поиска |
|----------|--------------|---------------|
| **Тип кузова** | `car_modifications.body_type` | В LLM передавать **справочник уникальных значений body_type из БД**; просить подобрать значение строго по этому справочнику. Поиск по точному значению. |
| **Марка** | `car_brands.name` | Просить LLM отдать название в **общепринятом виде**. Поиск — **текстовый** по `car_brands.name` → получение `brand_id` → фильтрация `cars.brand_id`. |
| **Модель** | `car_models.name` | Просить LLM отдать название в **общепринятом виде**. Поиск — **текстовый** по `car_models.name` → получение `model_id` → фильтрация `cars.model_id`. |

> **Примечание:** В справочниках нет бюджета, коробки передач, типа топлива и страны-производителя — эти параметры не участвуют в поиске. При необходимости в будущем можно добавить дополнительные справочные таблицы.

**Основные шаги при получении вопроса пользователя:**

1. **Шаг 1. Извлечение параметров подбора из истории переписки (LLM)**
   По истории переписки при помощи LLM получаем в **структурированном виде** параметры подбора, которые заявил пользователь.
   Нас интересуют параметры: **тип кузова**; **марка**; **модель**.
   - Для **типа кузова** в LLM передавать **справочник из нашей БД** (уникальные значения `body_type` из таблицы `car_modifications`) и просить подобрать значение строго на основе этого справочника.
   - Для **марки** и **модели** — просить отдать их название в общепринятом виде.

2. **Шаг 2. Поиск и ответ**
   - Если на Шаге 1 удалось **однозначно определить хотя бы 3 параметра** — используем их для запроса на поиск подходящей машины в нашей БД. Тип кузова ищем по **точному значению из справочника**, а марку и модель — **текстовым поиском** (через `car_brands.name` → `brand_id` и `car_models.name` → `model_id`).
   - Если найдена **хотя бы одна** подходящая машина в БД — отвечаем пользователю в чат и сообщаем, что считаем подходящими для него этот список машин (по каждой показываем все известные нам характеристики).
   - Если на Шаге 1 **не удалось определить 3 параметра** — отвечаем пользователю в чат в дружелюбной форме и задаём дополнительные вопросы.

**Важно:** текст ответа пользователю должен **генерироваться отдельным запросом к LLM**, в который передаются все нужные данные для его генерации.

### 9.4. Промпты и логирование

- **Промпты** для запросов к LLM необходимо **вынести в константы** (отдельный модуль/файл).
- Предусмотреть **логирование всех взаимодействий пользователя с бэкендом**: в БД сохраняются все этапы — сообщение пользователя, промпты и запросы к LLM, ответы от LLM, комментарии по логике принятия решений алгоритма (например: «не удалось определить параметры, поэтому задаём вопросы; вопросы генерируем с помощью LLM»).

---

**Документ готов к использованию кодинг-агентами.** Рекомендуемый порядок реализации: Backend B1–B9 (инфраструктура и авторизация), Frontend F1–F8 и F15–F16 (вход и роутинг), затем B10–B15 и F9–F14 (чат, DeepSeek API, поиск авто, UI чата и результатов).

---

## 10. Ревью архитектора-критика

Ревью проведено по чеклисту субагента «Системный архитектор — критик».

### Резюме

- **Вердикт:** Готово к реализации с учётом рекомендаций.
- **Оценка по категориям:** Executive Summary ✅, Архитектурная диаграмма ✅, Структура компонентов ✅, API/интерфейсы ✅, Модель данных ✅, План реализации ✅, Acceptance Criteria ✅.

### Критические замечания (блокируют реализацию)

Критических пробелов не выявлено. Контракты API, DDL, порядок задач и критерии приёмки заданы однозначно.

### Рекомендации по улучшению (не блокируют)

1. **Раздел 4 (API):** Явно указать для GET /api/v1/chat/sessions коды ошибок (401 при отсутствии токена).
2. **Раздел 5.2:** Подтвердить явно, что при ON DELETE CASCADE для `sessions` каскадно удаляются `chat_messages` и `search_parameters` (зависит от настроек FK в миграции).
3. **Раздел 6 (План):** ~~В задаче B10 зафиксировать имя модели Ollama~~ ✅ Решено: используется DeepSeek API (deepseek-chat), DEEPSEEK_API_KEY в .env.example.
4. **Раздел 9.3 vs 4.2:** ~~Уточнить соответствие «2 параметра» в п. 9.3 и «≥3 параметров» в разделе 4.2~~ ✅ Решено: единый порог — не менее 3 параметров (MIN_PARAMS_FOR_SEARCH = 3) зафиксирован в разделе 9.3 и в коде.

### Пропущенные аспекты

- **Мониторинг и логирование:** Не описаны метрики (латентность API, ошибки DeepSeek), структура логов и их ротация.
- **Rate limiting:** Не указан для auth и chat эндпоинтов (при публичном деплое желательно).
- **CORS:** В разделе 3.2 упомянуто «разрешить origin фронтенда», но не заданы конкретные `origins` (например для dev/prod).

### Альтернативные риски

- **Версионирование API:** Префикс `/api/v1` зафиксирован; план миграции на v2 при изменении контрактов не описан (приемлемо для MVP).
- **Импорт cars.xml:** В B15 указан URL Yandex; при недоступности URL нужен явный fallback на локальный файл и документирование формата полей XML.
