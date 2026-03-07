# CarMatch Frontend

Это frontend часть приложения CarMatch - интерактивного AI-консультанта по подбору автомобилей.

## Запуск приложения

Для запуска приложения в режиме разработки выполните:

```bash
npm install
npm run dev
```

После этого приложение будет доступно по адресу http://localhost:3000

**Важно:** После запуска команды `npm run dev` приложение будет доступно в браузере по адресу http://localhost:3000.
Вам нужно вручную открыть браузер и перейти по этому адресу, так как приложение представляет собой динамический
React-интерфейс, который требует JavaScript для отображения содержимого.

## Особенности локальной версии

В данной локальной версии:

- Используются mock-данные вместо реальных API вызовов
- Функционал авторизации эмулируется без обращения к backend
- Интерфейс демонстрирует основные элементы приложения
- Все данные хранятся локально в браузере

## Тестирование

Для запуска тестов выполните:

```bash
npm run test        # режим watch
npm run test:run    # однократный прогон
```

Используются Vitest, React Testing Library и jsdom.

## Стек технологий

- React 18+
- TypeScript
- Vite
- CSS Modules

## Админ-панель

Доступна пользователям с ролью администратора (`is_admin`). После входа через общую страницу `/login` администратор перенаправляется в админ-панель.

**Маршруты:**

- `/admin` — перенаправление на `/admin/cars`
- `/admin/cars` — управление автомобилями (список, добавление, редактирование, удаление)
- `/admin/dialogs` — список диалогов (сессий чата)
- `/admin/dialogs/:sessionId` — просмотр диалога по ID сессии
- `/admin/users` — список пользователей
- `/admin/users/:userId/dialogs` — диалоги конкретного пользователя

Защита маршрутов: `AdminProtectedRoute` проверяет наличие токена и флага `is_admin`; при отсутствии прав выполняется редирект на `/login`.

## Структура проекта

```
src/
├── App.tsx, App.css, App.test.tsx   # Корневой компонент: роутинг, провайдеры (Query, Auth)
├── index.tsx, index.css             # Точка входа, глобальные стили
├── vite-env.d.ts                    # Типы Vite (import.meta.env и т.д.)
│
├── api/                             # Клиент и методы работы с backend
│   ├── client.ts                    # axios-клиент (baseURL, Bearer, перехватчики)
│   ├── auth.ts                      # register, login, получение текущего пользователя
│   ├── chat.ts                      # отправка сообщений чата, сессии
│   └── cars.ts                      # поиск/получение автомобилей (для чата и карточек)
│
├── components/                      # Переиспользуемые UI-компоненты
│   ├── ProtectedRoute.tsx           # Защита маршрутов: редирект на /login без токена
│   ├── Chat/                        # Блок чата
│   │   ├── MessageInput.tsx         # Поле ввода и кнопка отправки сообщения
│   │   └── MessageList.tsx          # Список сообщений (пользователь / ассистент)
│   ├── ChatLayout/                  # Макет страницы чата
│   │   ├── ChatLayout.tsx           # Обёртка: сайдбар + область чата
│   │   └── ChatSidebar.tsx         # Список сессий, создание новой, переключение
│   └── CarResults/                  # Результаты подбора авто
│       ├── CarResults.tsx           # Сетка карточек автомобилей
│       └── CarDetailModal.tsx       # Модальное окно с деталями автомобиля
│
├── contexts/
│   └── AuthContext.tsx              # Состояние авторизации: token, user, login/logout
│
├── pages/                           # Страницы приложения (по одному на маршрут)
│   ├── AuthPage.tsx                 # /login — форма входа/регистрации
│   └── ChatPage.tsx                 # /chat, /chat/:sessionId — чат и результаты подбора
│
├── constants/
│   └── searchMessages.ts            # Тексты системных сообщений чата (поиск и т.д.)
│
├── test/
│   └── setup.ts                     # Настройка Vitest (глобальные моки, jsdom)
│
└── admin/                           # Админ-панель (доступ по is_admin)
    ├── api/                         # Запросы к админ-эндпоинтам backend
    │   ├── adminCars.ts             # CRUD автомобилей
    │   ├── adminUsers.ts            # Список пользователей, профиль, удаление
    │   └── adminSessions.ts         # Список сессий, детали диалога, удаление
    ├── components/
    │   ├── AdminLayout/             # Общий layout админки: навбар, меню, outlet
    │   │   ├── AdminLayout.tsx
    │   │   └── AdminLayout.module.css
    │   └── AdminProtectedRoute.tsx  # Проверка is_admin, редирект на /login
    ├── contexts/
    │   └── AdminAuthContext.tsx     # Обёртка над AuthContext для админки (опционально)
    └── pages/
        ├── AdminCarsPage.tsx        # /admin/cars — таблица авто, добавление/редактирование
        ├── AdminDialogsPage.tsx     # /admin/dialogs — список диалогов
        ├── AdminDialogDetailPage.tsx # /admin/dialogs/:sessionId — сообщения диалога
        ├── AdminUsersPage.tsx       # /admin/users — список пользователей
        ├── AdminUserDialogsPage.tsx # /admin/users/:userId/dialogs — диалоги пользователя
        └── AdminLoginPage.tsx       # Страница входа в админку (редирект на /login)
```

Стили компонентов: рядом с TSX-файлами используются CSS Modules (`.module.css`). Тесты лежат рядом с компонентами (`*.test.tsx`) или в тех же папках.
