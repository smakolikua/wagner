# 📦 Інструкція з встановлення

## Варіант 1 — Локально (розробка)

```bash
# Розпакувати
unzip fahrtenbuch_bot_v6.zip && cd fahrtenbuch_bot

# Середовище
python -m venv venv
source venv/bin/activate   # Linux/Mac
# venv\Scripts\activate    # Windows

# Залежності
pip install -r requirements.txt

# Конфіг
cp .env.example .env
nano .env   # → вставте BOT_TOKEN

# Запуск
python -m bot.main
```

При успішному старті побачите:
```
INFO  Starting Fahrtenbuch Bot v4...
INFO  Database ready.
INFO  Scheduler started.
INFO  Bot running. Ctrl+C to stop.
```

---

## Варіант 2 — Railway.app (безкоштовно, рекомендовано)

**Крок 1.** Завантажте на GitHub:
```bash
git init && git add .
git commit -m "Fahrtenbuch Bot"
git remote add origin https://github.com/YOUR/fahrtenbuch-bot.git
git push -u origin main
```

**Крок 2.** Відкрийте [railway.app](https://railway.app):
- New Project → Deploy from GitHub → обрати репозиторій
- Variables → додати `BOT_TOKEN=ваш_токен`
- Deploy → бот запустився!

---

## Варіант 3 — Docker (VPS/сервер)

```bash
cp .env.example .env
# Відредагуйте .env

# Запуск (SQLite)
docker-compose up -d bot

# Запуск з PostgreSQL
docker-compose up -d

# Логи
docker-compose logs -f bot

# Зупинити
docker-compose down
```

---

## Налаштування `.env`

| Змінна | Обов'язково | Опис |
|---|---|---|
| `BOT_TOKEN` | ✅ | Токен від @BotFather |
| `DATABASE_URL` | — | SQLite за замовч. |
| `ANTHROPIC_API_KEY` | — | Для OCR чеків |
| `GOOGLE_MAPS_API_KEY` | — | Кращий геокодинг |
| `GEOFENCE_RADIUS_METERS` | — | 100 за замовч. |
| `TIMEZONE` | — | Europe/Berlin |
| `ADMIN_TELEGRAM_ID` | — | Для /backup, /broadcast |
| `SENTRY_DSN` | — | Моніторинг помилок |
| `BOT_WEBHOOK_URL` | — | Production webhook |

---

## Перший запуск — що зробити

1. `/start` → введіть ім'я → оберіть мову
2. `/cars` → додайте авто (марка, модель, номер, пробіг)
3. `/addresses` → додайте домашню адресу (`Heimatadresse`)
4. Надішліть **фото чека** → бот розпізнає автоматично
5. `/track` → оберіть авто → надішліть **Live Location**
6. `/report` → отримайте PDF Fahrtenbuch
7. `/taxreport` → отримайте EÜR PDF

---

## OCR чеків — налаштування

Для автоматичного розпізнавання чеків потрібен Anthropic API key:

1. Зареєструйтесь на [console.anthropic.com](https://console.anthropic.com)
2. Settings → API Keys → Create Key
3. Додайте в `.env`: `ANTHROPIC_API_KEY=sk-ant-...`

**Без API key** — чеки можна вносити вручну через `/newreceipt`.

---

## CSV-імпорт адрес

Формат файлу `addresses.csv`:
```csv
name,address,type
Heimat,Musterstraße 12 80331 München,Heimatadresse
Büro München,Leopoldstraße 100 80802 München,Büro
Kunde Müller,Hauptstraße 1 85356 Freising,Kunde
```

Типи: `Heimatadresse`, `Kunde`, `Büro`, `Sonstiges`

Надішліть файл боту: `/addresses` → **📂 Імпорт CSV**

---

## Тести

```bash
python -m pytest tests/ -v
# 93 passed ✅
```

---

## Backup даних

```bash
# Вручну
cp fahrtenbuch.db backup_$(date +%Y%m%d).db

# Через бота (тільки для адміна)
/backup
```
