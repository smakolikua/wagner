# Fahrtenbuch Bot — Start Here

Це коротка інструкція, з чого почати після розпакування архіву.

## 1. Що всередині

- `bot/` — код Telegram-бота.
- `alembic/` — міграції бази даних.
- `tests/` — автоматичні тести.
- `requirements.txt` — Python-залежності.
- `.env.example` — шаблон конфігурації.
- `DEMO_GUIDE.md` — сценарій показу продукту замовнику.
- `QA_REPORT.md` — звіт про перевірки.
- `README.md` / `INSTALL.md` — повна документація проєкту.

## 2. Локальний запуск

```bash
cd fahrtenbuch_bot
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env
```

Відкрий `.env` і заповни мінімум:

```env
BOT_TOKEN=your_real_botfather_token
DATABASE_URL=sqlite+aiosqlite:///./fahrtenbuch.db
TIMEZONE=Europe/Berlin
```

Після цього запуск:

```bash
mkdir -p .mplconfig
MPLCONFIGDIR=.mplconfig .venv/bin/python -m bot.main
```

Успішний старт виглядає так:

```text
Starting Fahrtenbuch Bot v4...
Mode: POLLING
Bot running. Ctrl+C to stop.
```

## 3. Перевірка перед демо

```bash
MPLCONFIGDIR=.mplconfig .venv/bin/python -m pytest tests/ -q
PYTHONPYCACHEPREFIX=/tmp/fahrtenbuch_pycache MPLCONFIGDIR=.mplconfig .venv/bin/python -m compileall -q bot
.venv/bin/alembic upgrade head
```

Очікувано:

- тести проходять;
- бот запускається;
- Telegram webhook порожній, якщо працює polling;
- база створюється автоматично.

## 4. Що показувати замовнику

Використовуй `DEMO_GUIDE.md`.

Короткий порядок:

1. `/start` і реєстрація.
2. Додати авто.
3. Додати адреси.
4. Додати поїздку.
5. Додати чек вручну.
6. Додати дохід.
7. Згенерувати Fahrtenbuch PDF.
8. Згенерувати EÜR PDF.
9. Показати CSV/ZIP export.
10. Показати статистику.
11. Показати `/dashboard`.
12. Показати `/open`.
13. Показати `/audit`.
14. Сформувати `/steuerpaket`.
15. Показати `/team`.

## 5. PIN login і відновлення профілю

Після першої реєстрації бот показує користувачу 6-значний PIN.

Навіщо він потрібен:

- користувач може зайти з іншого Telegram-акаунта;
- вводить свій PIN;
- бот додає новий Telegram-акаунт як ще один вхід до існуючого профілю;
- авто, адреси, поїздки, чеки, доходи і налаштування підтягуються з його старої бази.

Багатокористувацький режим:

- кожен клієнт має окремий `user_id`;
- всі авто, адреси, поїздки, чеки, доходи і звіти фільтруються тільки за його `user_id`;
- таблиця `user_accounts` зв'язує Telegram-акаунти з профілями;
- один профіль може мати кілька Telegram-входів через PIN;
- різні клієнти не бачать дані один одного.

Команда для створення нового PIN:

```text
/my_pin
```

Попередній PIN після цього перестає працювати.

## 6. Нові demo-команди після аналізу конкурентів

```text
/dashboard
/open
/audit
/steuerpaket
/team
```

- `/dashboard` — зведення місяця: поїздки, business/private km, доходи, витрати, результат, відкриті задачі.
- `/open` — відкриті задачі перед звітом: активний GPS tracking, чеки без підтвердження, поїздки без нотаток.
- `/audit` — Änderungsprotokoll: останні зміни по профілю.
- `/steuerpaket` — ZIP для Steuerberater за поточний рік: CSV, README, Fahrtenbuch PDF, EÜR PDF.
- `/team` — owner бачить Telegram-доступи профілю і ролі `owner/driver`.

Smart address rules:

- якщо в ручному вводі поїздки користувач вводить назву або частину вже збереженої адреси, бот автоматично прив'язує поїздку до цієї адреси;
- це зменшує дублікати і робить журнал акуратнішим.

## 7. Важливі ключі

- `BOT_TOKEN` — обов'язковий, береться у BotFather.
- `ANTHROPIC_API_KEY` — потрібен тільки для OCR фото чеків.
- `GOOGLE_MAPS_API_KEY` — опціонально для кращого геокодингу.
- `SENTRY_DSN` — опціонально для моніторингу.
- `ADMIN_TELEGRAM_ID` — твій Telegram ID для admin-команд.
- `STORAGE_BOT_TOKEN` — токен другого Telegram-бота для backup storage.
- `STORAGE_CHAT_ID` — ID приватного storage-чату або каналу.

Без `ANTHROPIC_API_KEY` ручне додавання чеків працює, але автоматичне OCR фото чеків не буде доступне.

## 8. Другий Telegram-бот як storage backup

Telegram-бот не замінює SQL-базу даних, але другий бот можна використовувати як backup storage: основний Fahrtenbuch Bot працює з БД, а storage bot надсилає копію БД у приватний канал/групу.

Як налаштувати:

1. У BotFather створити другого бота, наприклад `Fahrtenbuch Storage Bot`.
2. Створити приватний Telegram-канал або групу `Fahrtenbuch Storage`.
3. Додати другого бота в цей канал/групу як admin.
4. Отримати `chat_id` каналу/групи.
5. У `.env` додати:

```env
ADMIN_TELEGRAM_ID=your_telegram_user_id
STORAGE_BOT_TOKEN=storage_bot_token_from_botfather
STORAGE_CHAT_ID=-1001234567890
```

Admin-команди:

```text
/storage_status
/storage_backup
```

`/storage_backup` відправить SQLite backup у storage-чат через другого бота.

Для PostgreSQL production backup краще робити через `pg_dump`, а в Telegram storage надсилати готовий dump/архів.

## 9. Production / Docker

Для Docker:

```bash
cp .env.example .env
# заповнити BOT_TOKEN, POSTGRES_PASSWORD, DATABASE_URL
docker-compose up -d
```

Для Railway:

1. Завантажити код у GitHub.
2. Підключити repo до Railway.
3. Додати env variables: `BOT_TOKEN`, `DATABASE_URL`.
4. Deploy.

## 10. Безпека

Не передавай реальний `.env` клієнту або в публічний репозиторій. Якщо token випадково показували в чаті або документах, перевипусти його через BotFather.
