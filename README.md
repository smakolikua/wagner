# 🚗💰 Fahrtenbuch + Steuerbot

**Telegram-бот для самозайнятих у Германії** — веде офіційний Fahrtenbuch, сканує чеки через AI, рахує EÜR та готує всі документи для Finanzamt.

> Жоден конкурент не поєднує GPS-трекінг + OCR чеків + EÜR + Telegram в одному продукті.

---

## 🎯 Для кого

| Аудиторія | Що отримує |
|---|---|
| Фрілансери / Selbstständige | Fahrtenbuch + чеки в одному місці |
| Kleinunternehmer | EÜR без бухгалтера |
| Werkvertrag / GbR | CSV-експорт для DATEV |
| Україномовні в DE/AT/CH | 🇩🇪🇺🇦🇷🇺🇬🇧 повна підтримка 4 мов |

---

## ✨ Що вміє бот

### 🚗 Fahrtenbuch (журнал поїздок)
- GPS Live Location → автоматична фіксація поїздок
- Dwell detection: зупинка ≥ 60 сек = запис прибуття
- Smart геофенс (50–200 м, налаштовується)
- Ручне додавання та редагування поїздок
- PDF Fahrtenbuch: Datum · Abfahrt · Ziel · km · Zweck

### 🧾 Belegscanner (чеки)
- Фото чека → Claude Vision AI → автоматичне розпізнавання
- Сума, дата, постачальник, ПДВ (0% / 7% / 19%)
- 12 категорій витрат (§ 4 EStG): Bürobedarf, Kfz, Reise, Bewirtung…
- Ручне введення, фільтр по місяцях та категоріях
- Статистика витрат

### 💶 Einnahmen (доходи)
- Введення доходів з номером рахунку і клієнтом
- Підтримка Kleinunternehmer (без ПДВ)
- Місячна статистика

### 💰 EÜR Звіт
- Einnahmenüberschussrechnung (§ 4 Abs. 3 EStG)
- Автоматично бере дані з поїздок, чеків і доходів
- Fahrtkosten: 0,30 €/km pauschal
- ПДВ підсумок (Vorsteuer / Zahllast)
- PDF зі структурою: Einnahmen → Fahrtkosten → BA → Ergebnis → Unterschrift

### 📤 Export CSV
- Сумісно з Excel, DATEV, Lexware, LibreOffice
- Окремо: чеки / поїздки / доходи
- Або все разом у ZIP-архіві

### 📊 Статистика та нагадування
- Графіки пробігу (8 тижнів) + кругова діаграма
- Щомісячне нагадування згенерувати звіт
- 10-го числа — нагадування USt-Voranmeldung
- Щовечора — нагадування внести чеки

---

## 🏗 Архітектура

```
fahrtenbuch_bot/
├── bot/
│   ├── handlers/          # 15 модулів: auth, vehicles, addresses, trips,
│   │   │                  #   tracking, reports, receipts, tax_handler,
│   │   │                  #   income, export_handler, settings, help,
│   │   │                  #   stats, admin, menu_router
│   │   └── menu_router.py # Єдиний роутер кнопок меню (4 мови)
│   ├── services/          # 9 модулів: geo, track_store, pdf_report,
│   │   │                  #   csv_import, csv_export, ocr_service,
│   │   │                  #   tax_report, stats_chart, validators
│   ├── models/            # 10 моделей БД
│   │   ├── user.py        # geofence_radius per-user
│   │   ├── vehicle.py
│   │   ├── address.py
│   │   ├── trip.py
│   │   ├── live_session.py
│   │   ├── category.py    # 12 системних категорій EStG
│   │   ├── receipt.py     # OCR + manual чеки
│   │   ├── income.py      # Einnahmen
│   │   └── tax_period.py
│   ├── i18n/
│   │   └── translator.py  # 103 ключі × 4 мови (DE/UA/RU/EN)
│   ├── schedulers/
│   │   └── reminder.py    # 5 APScheduler задач
│   ├── middlewares/       # DbSession, Auth, RateLimit
│   ├── config.py          # Pydantic Settings
│   ├── database.py        # engine + category seed
│   └── main.py            # polling / webhook auto-switch
├── alembic/
│   └── versions/          # 0001..0005 міграції
├── tests/                 # 11 файлів, 93 тести
├── .github/workflows/     # CI/CD: test → build → deploy
├── Dockerfile             # multi-stage
├── docker-compose.yml     # bot + postgres + migrate
├── railway.toml           # Railway.app деплой
└── Procfile
```

---

## 📦 Технічний стек

| Компонент | Технологія |
|---|---|
| Telegram framework | aiogram 3.13 |
| База даних | SQLite (dev) → PostgreSQL (prod) |
| ORM + міграції | SQLAlchemy 2.0 + Alembic |
| AI / OCR | Claude Vision (claude-sonnet-4) |
| PDF | ReportLab |
| Charts | matplotlib |
| Geocoding | Geopy (Nominatim) |
| Scheduler | APScheduler |
| HTTP client | httpx |
| Monitoring | Sentry SDK |
| Logging | Loguru |
| Deploy | Docker + Railway.app / VPS |

---

## 🚀 Швидкий старт

```bash
# 1. Розпакувати
unzip fahrtenbuch_bot_v6.zip && cd fahrtenbuch_bot

# 2. Середовище
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# 3. Конфіг
cp .env.example .env
# Відредагуйте .env — вставте BOT_TOKEN

# 4. Запуск
python -m bot.main
```

### Docker (рекомендовано для продакшн)
```bash
cp .env.example .env
# Відредагуйте .env
docker-compose up -d
```

### Railway.app (безкоштовно)
1. Завантажте код на GitHub
2. Підключіть до Railway.app
3. Додайте змінну `BOT_TOKEN`
4. Deploy

---

## ⚙️ Конфігурація `.env`

```env
BOT_TOKEN=your_token_here

# БД (SQLite для старту)
DATABASE_URL=sqlite+aiosqlite:///./fahrtenbuch.db

# Webhook (порожньо = polling)
BOT_WEBHOOK_URL=
WEBHOOK_PORT=8443

# AI для OCR чеків
# (якщо порожньо — OCR недоступний, тільки ручне введення)
ANTHROPIC_API_KEY=

# Геокодинг (порожньо = OpenStreetMap/Nominatim)
GOOGLE_MAPS_API_KEY=

# Геофенс за замовчуванням (метри)
GEOFENCE_RADIUS_METERS=100

# Timezone
TIMEZONE=Europe/Berlin

# Адмін (для /backup, /broadcast, /admin_stats)
# ADMIN_TELEGRAM_ID=123456789

# Sentry (порожньо = вимкнено)
# SENTRY_DSN=https://...@sentry.io/...

# Логування
LOG_LEVEL=INFO
LOG_FILE=logs/bot.log
```

---

## 📋 Команди бота

| Команда | Опис |
|---|---|
| `/start` | Реєстрація / головне меню |
| `/cars` | Автомобілі (CRUD) |
| `/addresses` | Адреси + CSV-імпорт |
| `/trips` | Журнал поїздок |
| `/newtrip` | Нова поїздка вручну |
| `/track` | Запустити GPS-трекінг |
| `/stoptrack` | Зупинити трекінг |
| `/trackstatus` | Статус активного трекінгу |
| `/report` | PDF Fahrtenbuch |
| `/receipts` | Чеки та витрати |
| `/newreceipt` | Додати чек вручну |
| `/incomes` | Доходи (Einnahmen) |
| `/addincome` | Додати дохід |
| `/taxreport` | EÜR PDF звіт |
| `/export` | CSV для бухгалтера / DATEV |
| `/stats` | Статистика + графіки |
| `/settings` | Налаштування (мова, геофенс) |
| `/backup` | Резервна копія БД (адмін) |
| `/help` | Повна довідка |

> **Підказка:** фото чека можна надіслати прямо в чат — бот розпізнає автоматично!

---

## 🔬 Тести

```bash
python -m pytest tests/ -v
```

| Файл | Тести | Покриття |
|---|---|---|
| test_geo.py | 11 | GPS, haversine, dwell, accumulator |
| test_i18n.py | 9 | 4 мови, format, fallback |
| test_pdf.py | 4 | Fahrtenbuch PDF |
| test_csv.py | 8 | CSV парсинг адрес |
| test_receipts.py | 17 | OCR, Receipt model, Categories |
| test_tax_report.py | 6 | EÜR PDF |
| test_validators.py | 10 | mileage, date, pdf |
| test_csv_export.py | 17 | CSV/ZIP export |
| test_income.py | 9 | Income model |
| **Всього** | **93** | ✅ |

---

## 📊 Порівняння з конкурентами

| Функція | Vimcar | WISO Steuer | Taxfix | **Наш бот** |
|---|---|---|---|---|
| GPS Fahrtenbuch | ✅ (донгл) | ❌ | ❌ | ✅ (Live Location) |
| OCR чеків | ❌ | ✅ | ❌ | ✅ (Claude AI) |
| EÜR звіт | ❌ | ✅ | ❌ | ✅ |
| ПДВ підсумок | ❌ | ✅ | ❌ | ✅ |
| Telegram | ❌ | ❌ | ✅ (WhatsApp) | ✅ |
| DE/UA/RU/EN | ❌ | ❌ | ❌ | ✅ |
| DATEV CSV | ❌ | ✅ | ❌ | ✅ |
| Self-hosted | ❌ | ❌ | ❌ | ✅ |
| Вартість | €15+/міс | €29/рік | €39/рік | **безкоштовно** |

---

## 📜 Ліцензія

MIT License — вільне використання, зміна і розповсюдження.

---

*Fahrtenbuch Bot — зроблено для самозайнятих у Германії.*
