# 🗺️ Roadmap — Fahrtenbuch + Steuerbot

## ✅ Фаза 1 — MVP (ЗАВЕРШЕНО)
- [x] Реєстрація через /start (FSM, вибір мови)
- [x] CRUD автомобілів (/cars)
- [x] CRUD адрес + CSV-імпорт (/addresses)
- [x] Ручне додавання поїздок (/newtrip, /trips)
- [x] PDF Fahrtenbuch (/report)
- [x] Middleware: DbSession, Auth
- [x] Моделі: User, Vehicle, Address, Trip, LiveSession

## ✅ Фаза 2 — GPS-трекінг (ЗАВЕРШЕНО)
- [x] TrackAccumulator — smooth distance по точках
- [x] Dwell detection — зупинка ≥ 60 сек у радіусі 30 м
- [x] Геофенсинг — автозапис при прибутті до відомої адреси
- [x] Запит мети при невідомій зупинці + збереження нової адреси
- [x] /trackstatus — статус активної сесії
- [x] /stoptrack — підсумок сесії (км, час, поїздки)
- [x] APScheduler: щомісячне нагадування, тижнева неактивність, cleanup
- [x] RateLimitMiddleware
- [x] /stats — статистика + графіки (matplotlib)

## ✅ Фаза 3 — Розширений функціонал (ЗАВЕРШЕНО)
- [x] Редагування поїздок (FSM: дата, мета, нотатки, пробіг)
- [x] Повна i18n: DE / UA / RU / EN (103 ключі)
- [x] Per-user geofence_radius (50–200 м)
- [x] Діаграми: стовпчаста (8 тижнів) + кругова
- [x] /backup, /broadcast, /admin_stats (admin)
- [x] Universal menu_router — кнопки меню для всіх 4 мов

## ✅ Фаза 4 — Деплой (ЗАВЕРШЕНО)
- [x] Alembic міграції (0001..0005)
- [x] Webhook + Polling авто-вибір
- [x] Docker multi-stage build (non-root user)
- [x] docker-compose: bot + postgres + migrate + adminer
- [x] Sentry + Loguru (rotation 10MB/7d)
- [x] GitHub Actions CI/CD (test → build → deploy)
- [x] railway.toml + Procfile

## ✅ Фаза 5 — Belegscanner + EÜR (ЗАВЕРШЕНО)
- [x] Модель Category (12 системних за § EStG)
- [x] Модель Receipt (OCR + manual)
- [x] Модель TaxPeriod
- [x] Claude Vision OCR: фото → JSON → підтвердження
- [x] Receipt CRUD + фільтр по місяцю/категорії
- [x] Ручне введення чеків (ManualReceiptFSM)
- [x] EÜR PDF: Einnahmen → Fahrtkosten → BA → Ergebnis → USt
- [x] Alembic 0003 (categories, receipts, tax_periods)

## ✅ Фаза 6 — Доходи, Export, Нагадування (ЗАВЕРШЕНО)
- [x] Модель Income (Einnahmen з рахунком, клієнтом, ПДВ)
- [x] /incomes — список, місячна статистика, CRUD
- [x] /addincome — FSM: дата → сума → ПДВ → клієнт → рахунок
- [x] Kleinunternehmer підтримка (без ПДВ)
- [x] EÜR автоматично бере доходи з таблиці Income
- [x] Фільтр чеків: по місяцю / категорії / тип (ділові/приватні)
- [x] CSV Export: receipts / trips / incomes / ZIP
- [x] ZIP сумісний з Excel, DATEV, Lexware
- [x] Щовечірнє нагадування внести чеки (20:00)
- [x] 10-го числа — нагадування USt-Voranmeldung
- [x] Alembic 0005 (incomes + indexes)
- [x] Тести: 93/93 ✅

---

## 📊 Статистика проекту

| Метрика | Значення |
|---|---|
| Python файлів | 58 (bot) + 11 (tests) |
| Рядків коду | ~8,600 |
| Handler модулів | 15 |
| Service модулів | 9 |
| Моделей БД | 10 |
| Alembic міграцій | 5 |
| FSM класів | 15 (62 стани) |
| i18n ключів | 103 × 4 мови |
| Тестів | 93/93 ✅ |
| Мови | DE / UA / RU / EN |

---

## 🔜 Фаза 7 — Наступні покращення (заплановано)

### Пріоритет HIGH
- [ ] **Anthropic API Key у конфігу** — зараз OCR потребує API key, треба додати в .env + перевірку при старті
- [ ] **Прив'язка чека до поїздки** — при перегляді поїздки показувати прикріплені чеки
- [ ] **Квартальна USt-Voranmeldung PDF** — автоматичний розрахунок Zahllast

### Пріоритет MEDIUM
- [ ] **Webhook SSL** — Nginx reverse proxy з Let's Encrypt для production webhook
- [ ] **PostgreSQL migration script** — автоматичний перенос даних з SQLite
- [ ] **Recurring trips** — шаблони для регулярних поїздок (наприклад, щоденна поїздка на роботу)
- [ ] **Multi-car report** — один PDF для кількох авто
- [ ] **Income invoice PDF** — генерація рахунку-фактури (Rechnung) з шаблоном

### Пріоритет LOW
- [ ] **Lexoffice / sevDesk API** — пряма інтеграція з бухгалтерськими сервісами
- [ ] **ELSTER XML** — експорт для електронної подачі до Finanzamt
- [ ] **Steueridentifikationsnummer** — зберігання та автозаповнення у звітах
- [ ] **Dark mode PDF** — альтернативний стиль PDF
- [ ] **Inline mode** — швидке додавання чека через @bot_name в будь-якому чаті

---

## 🐛 Відомі обмеження

| Обмеження | Статус | Workaround |
|---|---|---|
| OCR потребує Anthropic API | Треба налаштувати | Ручне введення /newreceipt |
| Nominatim rate limit 1 req/sec | Кешування в пам'яті | Додати Google Maps API key |
| SQLite не підтримує concurrent writes | Для 1 юзера OK | PostgreSQL для multi-user |
| Live Location тільки 8 годин | Обмеження Telegram | Перезапустити /track |
| Charts потребують matplotlib | ~50 MB RAM | Вимкнути якщо мало RAM |

---

## 🚀 Деплой зараз (Railway.app — безкоштовно)

```bash
# 1. GitHub
git init && git add . && git commit -m "init"
git remote add origin https://github.com/USER/fahrtenbuch-bot.git
git push -u origin main

# 2. Railway.app
# → New Project → Deploy from GitHub → вибрати репо
# → Variables → додати BOT_TOKEN

# 3. Готово! Бот живий.
```

---

*Останнє оновлення: Фаза 6 завершена. Наступна: Фаза 7.*
