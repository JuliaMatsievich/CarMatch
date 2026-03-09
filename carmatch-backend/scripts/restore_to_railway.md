# Восстановление дампа БД на Railway

## Копирование локальной БД на Railway

### Вариант 1: одной командой (pg_dump + psql)

Из корня репозитория (нужны `pg_dump` и `psql` в PATH):

```bash
pg_dump --no-owner --no-privileges --clean --if-exists "postgresql://carmatch:carmatch@localhost:5433/carmatch" | psql "postgresql://postgres:eVRcxncToZxpECmsv-nYt6ynJTotnz-7@trolley.proxy.rlwy.net:45413/railway"
```

Если локальная БД с другими учётными данными или портом — замени первый URL. Для Railway может понадобиться `?sslmode=require` в конце второго URL, если команда выдаст ошибку по SSL.

### Вариант 2: скрипт Python (без pg_dump)

Локальная БД должна быть запущена (по умолчанию `localhost:5433/carmatch`). Из `carmatch-backend`:

```bash
export REMOTE_DATABASE_URL="postgresql://postgres:ПАРОЛЬ@trolley.proxy.rlwy.net:45413/railway"
python scripts/copy_full_db_to_render.py
```

Скрипт применит миграции на Railway (если нужно), очистит таблицы и скопирует все данные (users, cars, car_brands, sessions и т.д.). Для другой локальной БД задайте `LOCAL_DATABASE_URL`.

---

Дамп уже создан в корне проекта: `carmatch.dump` (custom format, ~95 MB).

## Если нет команды pg_restore (Windows)

`pg_restore` входит в клиентские утилиты PostgreSQL. Варианты:

**Вариант A — через Docker** (удобно, не ставим PostgreSQL в систему):
```bash
cd C:\Julia\Learning\AI_Driven\CarMatch
docker run --rm -v "%CD%":/data -w /data postgres:16 pg_restore -d "ВСТАВЬТЕ_СЮДА_DATABASE_URL_ИЗ_RAILWAY" --no-owner --no-acl --clean --if-exists -F c carmatch.dump
```
Подставьте скопированную из Railway строку подключения (Variables → DATABASE_URL). В URL обычно уже есть `?sslmode=require` или его нужно добавить.

**Вариант B — установить PostgreSQL**
- Скачайте [PostgreSQL для Windows](https://www.postgresql.org/download/windows/) и установите (достаточно «Command Line Tools» или полная установка).
- Добавьте в PATH папку `bin`, например: `C:\Program Files\PostgreSQL\16\bin`.
- Перезапустите терминал и выполните команды из шага 2 ниже.

## Шаги

1. **Скопируйте строку подключения к БД на Railway**
   - Railway → проект → сервис **pgvector** → вкладка **Variables**
   - Скопируйте значение **DATABASE_URL** или **POSTGRES_URL** (вид: `postgresql://USER:PASSWORD@HOST:PORT/RAILWAY`)

2. **Восстановите дамп** (из корня репозитория CarMatch, нужны клиенты PostgreSQL: `pg_restore`):

   **Linux / macOS / Git Bash:**
   ```bash
   cd /path/to/CarMatch
   pg_restore -d "postgresql://USER:PASSWORD@HOST:PORT/RAILWAY?sslmode=require" \
     --no-owner --no-acl --clean --if-exists -F c carmatch.dump
   ```
   Подставьте свою строку вместо `postgresql://...` (если в URL уже есть `?sslmode=require`, не дублируйте).

   **Windows (cmd):**
   ```cmd
   cd C:\path\to\CarMatch
   set PGPASSWORD=your_password
   pg_restore -d "postgresql://USER@HOST:PORT/RAILWAY?sslmode=require" --no-owner --no-acl --clean --if-exists -F c carmatch.dump
   ```
   Или вставьте полный URL в одну кавычку и выполните:
   ```cmd
   pg_restore -d "ВСТАВЬТЕ_СЮДА_DATABASE_URL_ИЗ_RAILWAY" --no-owner --no-acl --clean --if-exists -F c carmatch.dump
   ```

3. Если появятся ошибки вида «relation already exists» — на Railway уже могли быть созданы таблицы миграциями. Тогда можно попробовать только данные (осторожно, может дублировать строки):
   ```bash
   pg_restore -d "ВАШ_URL" --no-owner --no-acl --data-only -F c carmatch.dump
   ```

После успешного восстановления бэкенд на Railway будет использовать эту базу (убедитесь, что в сервисе бэкенда в Variables задан тот же DATABASE_URL).
