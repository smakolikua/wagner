# Render Deploy — Fahrtenbuch Bot

Цей файл описує, як запустити бота на Render, щоб він працював без локального комп'ютера.

## 1. Що вже підготовлено

- `render.yaml` — Render Blueprint.
- `runtime.txt` — Python 3.11 для Render.
- `Procfile` — fallback для worker запуску.
- `bot/config.py` автоматично конвертує Render Postgres URL у `postgresql+asyncpg://`.
- `startCommand` у Render виконує:

```bash
alembic upgrade head && python -m bot.main
```

Тобто Render спочатку оновить базу, а потім запустить Telegram polling.

## 2. Архітектура на Render

Blueprint створює:

- PostgreSQL database: `fahrtenbuch-db`
- Background Worker: `fahrtenbuch-bot`

Worker працює без HTTP-порту, бо Telegram bot використовує polling.

## 3. Перед деплоєм

Код потрібно залити в GitHub/GitLab/Bitbucket. Render не деплоїть напряму з локальної папки.

Не завантажувати в Git:

- `.env`
- `.venv`
- `.venv311`
- `fahrtenbuch.db`
- `logs/`
- будь-які реальні токени

## 4. GitHub

Якщо GitHub CLI залогінений:

```bash
git init
git add .
git commit -m "Prepare Fahrtenbuch Bot for Render"
gh repo create fahrtenbuch-bot --private --source=. --remote=origin --push
```

Якщо GitHub CLI не залогінений:

```bash
gh auth login
```

Після логіну повторити команди вище.

## 5. Render Blueprint Deploy

1. Відкрити Render Dashboard.
2. Натиснути `New +`.
3. Обрати `Blueprint`.
4. Підключити GitHub repo з цим проєктом.
5. Render знайде `render.yaml`.
6. Натиснути `Apply`.
7. Render створить PostgreSQL і worker.

## 6. Environment variables

У Render треба заповнити секретні значення, які в `render.yaml` позначені як `sync: false`.

Обов'язково:

```env
BOT_TOKEN=...
```

Рекомендовано:

```env
ADMIN_TELEGRAM_ID=...
STORAGE_BOT_TOKEN=...
STORAGE_CHAT_ID=...
```

Опціонально:

```env
GOOGLE_MAPS_API_KEY=...
ANTHROPIC_API_KEY=...
SENTRY_DSN=...
```

`DATABASE_URL` Render підставить автоматично з `fahrtenbuch-db`.

## 7. Важливо про polling

Не можна одночасно запускати одного Telegram-бота локально і на Render з тим самим `BOT_TOKEN`.

Перед фінальним Render запуском зупинити локального бота:

```bash
pkill -f bot.main
```

## 8. Перевірка після деплою

У Render logs має бути:

```text
Running upgrade ... -> 0009_user_account_roles
Starting Fahrtenbuch Bot v4...
Mode: POLLING
Bot running. Ctrl+C to stop.
```

Після цього в Telegram:

1. Надіслати `/start`.
2. Перевірити `/dashboard`.
3. Перевірити `/open`.
4. Перевірити `/audit`.
5. Перевірити `/storage_status`, якщо storage bot налаштований.

## 9. Якщо бот не відповідає

Перевірити:

- Render worker status: `Live`.
- Render logs: немає помилки `BOT_TOKEN`.
- Render env: `BOT_TOKEN` заповнений.
- Локальний бот зупинений.
- У BotFather токен не перевипущений після деплою.
