"""
translator.py — проста система перекладів без зовнішніх залежностей.

Використання:
    from bot.i18n import t
    text = t("welcome", locale="ua", name="Max")
"""
from typing import Optional

SUPPORTED_LANGS = ("de", "ua", "ru", "en")

# ─── Словник перекладів ───────────────────────────────────────────────────────
_TRANSLATIONS: dict[str, dict[str, str]] = {

    # ── Загальне ─────────────────────────────────────────────────────────────
    "cancel_text": {
        "de": "❌ Abbrechen",
        "ua": "❌ Скасувати",
        "ru": "❌ Отмена",
        "en": "❌ Cancel",
    },
    "cancelled": {
        "de": "Abgebrochen.",
        "ua": "Скасовано.",
        "ru": "Отменено.",
        "en": "Cancelled.",
    },
    "saved": {
        "de": "✅ Gespeichert!",
        "ua": "✅ Збережено!",
        "ru": "✅ Сохранено!",
        "en": "✅ Saved!",
    },
    "error_number": {
        "de": "⚠️ Bitte eine Zahl eingeben, z.B.: 85000",
        "ua": "⚠️ Введіть число, наприклад: 85000",
        "ru": "⚠️ Введите число, например: 85000",
        "en": "⚠️ Please enter a number, e.g.: 85000",
    },
    "back": {
        "de": "◀️ Zurück",
        "ua": "◀️ Назад",
        "ru": "◀️ Назад",
        "en": "◀️ Back",
    },
    "yes": {"de": "✅ Ja", "ua": "✅ Так", "ru": "✅ Да", "en": "✅ Yes"},
    "no":  {"de": "❌ Nein", "ua": "❌ Ні", "ru": "❌ Нет", "en": "❌ No"},

    # ── Реєстрація ────────────────────────────────────────────────────────────
    "welcome": {
        "de": (
            "👋 Willkommen bei <b>Fahrtenbuch Bot</b>!\n\n"
            "Dieser Bot hilft Ihnen, ein offizielles Fahrtenbuch für das Finanzamt zu führen.\n\n"
            "Wie heißen Sie? Bitte Vor- und Nachnamen eingeben:"
        ),
        "ua": (
            "👋 Ласкаво просимо до <b>Fahrtenbuch Bot</b>!\n\n"
            "Цей бот допоможе вести офіційний журнал поїздок для Finanzamt.\n\n"
            "Як вас звати? Введіть ваше ім'я та прізвище:"
        ),
        "ru": (
            "👋 Добро пожаловать в <b>Fahrtenbuch Bot</b>!\n\n"
            "Этот бот поможет вести официальный журнал поездок для Finanzamt.\n\n"
            "Как вас зовут? Введите ваше имя и фамилию:"
        ),
        "en": (
            "👋 Welcome to <b>Fahrtenbuch Bot</b>!\n\n"
            "This bot helps you maintain an official mileage log for the Finanzamt.\n\n"
            "What is your name? Please enter your first and last name:"
        ),
    },
    "welcome_back": {
        "de": "👋 Willkommen zurück, <b>{name}</b>!\n\nWählen Sie eine Aktion:",
        "ua": "👋 З поверненням, <b>{name}</b>!\n\nОберіть дію:",
        "ru": "👋 С возвращением, <b>{name}</b>!\n\nВыберите действие:",
        "en": "👋 Welcome back, <b>{name}</b>!\n\nChoose an action:",
    },
    "choose_lang": {
        "de": "Großartig, <b>{name}</b>! 👍\n\nWählen Sie Ihre Sprache:",
        "ua": "Чудово, <b>{name}</b>! 👍\n\nОберіть мову інтерфейсу:",
        "ru": "Отлично, <b>{name}</b>! 👍\n\nВыберите язык интерфейса:",
        "en": "Great, <b>{name}</b>! 👍\n\nChoose your interface language:",
    },
    "reg_done": {
        "de": (
            "✅ Registrierung abgeschlossen!\n\n"
            "👤 Name: <b>{name}</b>\n"
            "🌐 Sprache: <b>{lang}</b>\n\n"
            "Fügen Sie jetzt Ihr erstes Fahrzeug hinzu: /cars"
        ),
        "ua": (
            "✅ Реєстрація завершена!\n\n"
            "👤 Ім'я: <b>{name}</b>\n"
            "🌐 Мова: <b>{lang}</b>\n\n"
            "Тепер додайте ваш перший автомобіль: /cars"
        ),
        "ru": (
            "✅ Регистрация завершена!\n\n"
            "👤 Имя: <b>{name}</b>\n"
            "🌐 Язык: <b>{lang}</b>\n\n"
            "Теперь добавьте ваш первый автомобиль: /cars"
        ),
        "en": (
            "✅ Registration complete!\n\n"
            "👤 Name: <b>{name}</b>\n"
            "🌐 Language: <b>{lang}</b>\n\n"
            "Now add your first vehicle: /cars"
        ),
    },
    "name_too_short": {
        "de": "Name zu kurz. Bitte erneut eingeben:",
        "ua": "Ім'я занадто коротке. Спробуйте ще раз:",
        "ru": "Имя слишком короткое. Попробуйте ещё раз:",
        "en": "Name too short. Please try again:",
    },

    # ── Головне меню ──────────────────────────────────────────────────────────
    "menu_cars":      {"de": "🚗 Meine Autos",  "ua": "🚗 Мої авто",      "ru": "🚗 Мои авто",      "en": "🚗 My Cars"},
    "menu_addresses": {"de": "📍 Adressen",     "ua": "📍 Адреси",         "ru": "📍 Адреса",         "en": "📍 Addresses"},
    "menu_trips":     {"de": "📋 Fahrten",      "ua": "📋 Поїздки",        "ru": "📋 Поездки",        "en": "📋 Trips"},
    "menu_newtrip":   {"de": "➕ Neue Fahrt",   "ua": "➕ Нова поїздка",   "ru": "➕ Новая поездка",  "en": "➕ New Trip"},
    "menu_track":     {"de": "📡 Tracking",     "ua": "📡 Трекінг",        "ru": "📡 Трекинг",        "en": "📡 Tracking"},
    "menu_report":    {"de": "📄 PDF-Bericht",  "ua": "📄 Звіт PDF",       "ru": "📄 Отчёт PDF",      "en": "📄 PDF Report"},
    "menu_settings":  {"de": "⚙️ Einstellungen","ua": "⚙️ Налаштування",   "ru": "⚙️ Настройки",     "en": "⚙️ Settings"},
    "menu_hint":      {"de": "Aktion wählen…",  "ua": "Оберіть дію...",    "ru": "Выберите действие…","en": "Choose action…"},

    # ── Авто ──────────────────────────────────────────────────────────────────
    "cars_title": {
        "de": "🚗 <b>Meine Fahrzeuge</b> ({count}):",
        "ua": "🚗 <b>Мої автомобілі</b> ({count}):",
        "ru": "🚗 <b>Мои автомобили</b> ({count}):",
        "en": "🚗 <b>My Vehicles</b> ({count}):",
    },
    "cars_empty": {
        "de": "🚗 Noch keine Fahrzeuge.\n\nFügen Sie Ihr erstes Fahrzeug hinzu:",
        "ua": "🚗 У вас ще немає жодного авто.\n\nДодайте перший автомобіль:",
        "ru": "🚗 У вас ещё нет автомобилей.\n\nДобавьте первый автомобиль:",
        "en": "🚗 No vehicles yet.\n\nAdd your first vehicle:",
    },
    "car_add":       {"de": "➕ Fahrzeug hinzufügen", "ua": "➕ Додати авто",     "ru": "➕ Добавить авто",    "en": "➕ Add Vehicle"},
    "car_ask_make":  {"de": "🚗 Fahrzeug hinzufügen\n\n<b>Marke</b> eingeben (z.B.: VW, BMW):", "ua": "🚗 Додавання авто\n\nВведіть <b>марку</b> (напр.: VW, BMW):", "ru": "🚗 Добавление авто\n\nВведите <b>марку</b> (напр.: VW, BMW):", "en": "🚗 Add Vehicle\n\nEnter <b>make</b> (e.g.: VW, BMW):"},
    "car_ask_model": {"de": "<b>Modell</b> eingeben (z.B.: Golf, X5):", "ua": "Введіть <b>модель</b> (напр.: Golf, X5):", "ru": "Введите <b>модель</b> (напр.: Golf, X5):", "en": "Enter <b>model</b> (e.g.: Golf, X5):"},
    "car_ask_plate": {"de": "<b>Kennzeichen</b> eingeben (z.B.: M-AB 1234):", "ua": "Введіть <b>держ. номер</b> (напр.: M-AB 1234):", "ru": "Введите <b>гос. номер</b> (напр.: M-AB 1234):", "en": "Enter <b>license plate</b> (e.g.: M-AB 1234):"},
    "car_ask_mileage": {"de": "<b>Aktuellen Kilometerstand</b> eingeben (nur Zahl, z.B.: 85000):", "ua": "Введіть <b>поточний пробіг</b> в км (тільки число, напр.: 85000):", "ru": "Введите <b>текущий пробег</b> в км (только число, напр.: 85000):", "en": "Enter <b>current mileage</b> in km (numbers only, e.g.: 85000):"},
    "car_added": {
        "de": "✅ Fahrzeug hinzugefügt!\n\n🚗 <b>{name}</b>\n📊 Kilometerstand: <b>{km:,} km</b>",
        "ua": "✅ Авто додано!\n\n🚗 <b>{name}</b>\n📊 Пробіг: <b>{km:,} км</b>",
        "ru": "✅ Авто добавлено!\n\n🚗 <b>{name}</b>\n📊 Пробег: <b>{km:,} км</b>",
        "en": "✅ Vehicle added!\n\n🚗 <b>{name}</b>\n📊 Mileage: <b>{km:,} km</b>",
    },
    "car_mileage_updated": {
        "de": "✅ Kilometerstand aktualisiert!\n🚗 {name}: <b>{km:,} km</b>",
        "ua": "✅ Пробіг оновлено!\n🚗 {name}: <b>{km:,} км</b>",
        "ru": "✅ Пробег обновлён!\n🚗 {name}: <b>{km:,} км</b>",
        "en": "✅ Mileage updated!\n🚗 {name}: <b>{km:,} km</b>",
    },
    "car_delete_confirm": {
        "de": "🗑 Fahrzeug <b>{name}</b> löschen?\n\n⚠️ Alle Fahrten werden ebenfalls gelöscht!",
        "ua": "🗑 Видалити <b>{name}</b>?\n\n⚠️ Всі поїздки цього авто також будуть видалені!",
        "ru": "🗑 Удалить <b>{name}</b>?\n\n⚠️ Все поездки этого авто тоже будут удалены!",
        "en": "🗑 Delete <b>{name}</b>?\n\n⚠️ All trips for this vehicle will also be deleted!",
    },
    "car_deleted": {
        "de": "✅ Fahrzeug <b>{name}</b> gelöscht.",
        "ua": "✅ Авто <b>{name}</b> видалено.",
        "ru": "✅ Авто <b>{name}</b> удалено.",
        "en": "✅ Vehicle <b>{name}</b> deleted.",
    },

    # ── Адреси ────────────────────────────────────────────────────────────────
    "addresses_title": {
        "de": "📍 <b>Gespeicherte Adressen</b> ({count}):",
        "ua": "📍 <b>Збережені адреси</b> ({count}):",
        "ru": "📍 <b>Сохранённые адреса</b> ({count}):",
        "en": "📍 <b>Saved Addresses</b> ({count}):",
    },
    "addresses_empty": {
        "de": "📍 Noch keine Adressen.\n\nFügen Sie die erste Adresse hinzu:",
        "ua": "📍 Адрес ще немає.\n\nДодайте першу адресу:",
        "ru": "📍 Адресов пока нет.\n\nДобавьте первый адрес:",
        "en": "📍 No addresses yet.\n\nAdd your first address:",
    },
    "addr_geocoding": {
        "de": "⏳ Adresse wird geocodiert…",
        "ua": "⏳ Геокодування адреси…",
        "ru": "⏳ Геокодирование адреса…",
        "en": "⏳ Geocoding address…",
    },
    "addr_added": {
        "de": "✅ Adresse hinzugefügt!\n\n📍 <b>{label}</b>\n🏷 Typ: {type}\n🗺 {addr}",
        "ua": "✅ Адресу додано!\n\n📍 <b>{label}</b>\n🏷 Тип: {type}\n🗺 {addr}",
        "ru": "✅ Адрес добавлен!\n\n📍 <b>{label}</b>\n🏷 Тип: {type}\n🗺 {addr}",
        "en": "✅ Address added!\n\n📍 <b>{label}</b>\n🏷 Type: {type}\n🗺 {addr}",
    },
    "addr_deleted": {
        "de": "✅ Adresse <b>{label}</b> gelöscht.",
        "ua": "✅ Адресу <b>{label}</b> видалено.",
        "ru": "✅ Адрес <b>{label}</b> удалён.",
        "en": "✅ Address <b>{label}</b> deleted.",
    },
    "addr_home_set": {
        "de": "✅ Heimatadresse gesetzt!",
        "ua": "✅ Домашня адреса встановлена!",
        "ru": "✅ Домашний адрес установлен!",
        "en": "✅ Home address set!",
    },

    # ── Поїздки ───────────────────────────────────────────────────────────────
    "trips_title": {
        "de": "📋 <b>Fahrten</b> (gesamt: {count}):",
        "ua": "📋 <b>Поїздки</b> (всього: {count}):",
        "ru": "📋 <b>Поездки</b> (всего: {count}):",
        "en": "📋 <b>Trips</b> (total: {count}):",
    },
    "trips_empty": {
        "de": "📋 Noch keine Fahrten.\n\nFügen Sie die erste Fahrt hinzu oder starten Sie GPS-Tracking:",
        "ua": "📋 Поїздок ще немає.\n\nДодайте першу поїздку або запустіть GPS-трекінг:",
        "ru": "📋 Поездок пока нет.\n\nДобавьте первую поездку или запустите GPS-трекинг:",
        "en": "📋 No trips yet.\n\nAdd your first trip or start GPS tracking:",
    },
    "trip_added": {
        "de": "✅ <b>Fahrt gespeichert!</b>\n\n📅 {date}\n📏 Distanz: <b>{km} km</b>\n{icon} {purpose}",
        "ua": "✅ <b>Поїздку записано!</b>\n\n📅 {date}\n📏 Відстань: <b>{km} км</b>\n{icon} {purpose}",
        "ru": "✅ <b>Поездка записана!</b>\n\n📅 {date}\n📏 Расстояние: <b>{km} км</b>\n{icon} {purpose}",
        "en": "✅ <b>Trip saved!</b>\n\n📅 {date}\n📏 Distance: <b>{km} km</b>\n{icon} {purpose}",
    },
    "trip_deleted": {
        "de": "✅ Fahrt gelöscht.",
        "ua": "✅ Поїздку видалено.",
        "ru": "✅ Поездка удалена.",
        "en": "✅ Trip deleted.",
    },
    "trip_updated": {
        "de": "✅ Fahrt aktualisiert.",
        "ua": "✅ Поїздку оновлено.",
        "ru": "✅ Поездка обновлена.",
        "en": "✅ Trip updated.",
    },
    "trip_ask_vehicle": {
        "de": "🚗 Fahrzeug wählen:",
        "ua": "🚗 Оберіть авто:",
        "ru": "🚗 Выберите авто:",
        "en": "🚗 Choose vehicle:",
    },
    "trip_ask_date": {
        "de": "📅 Datum eingeben (TT.MM.JJJJ oder 'heute'):",
        "ua": "📅 Введіть дату (ДД.ММ.РРРР або 'сьогодні'):",
        "ru": "📅 Введите дату (ДД.ММ.ГГГГ или 'сегодня'):",
        "en": "📅 Enter date (DD.MM.YYYY or 'today'):",
    },
    "trip_ask_from": {
        "de": "▶️ <b>Abfahrtsadresse</b> wählen:",
        "ua": "▶️ Оберіть адресу <b>звідки</b>:",
        "ru": "▶️ Выберите адрес <b>откуда</b>:",
        "en": "▶️ Choose <b>departure</b> address:",
    },
    "trip_ask_to": {
        "de": "🏁 <b>Zieladresse</b> wählen:",
        "ua": "🏁 Оберіть адресу <b>куди</b>:",
        "ru": "🏁 Выберите адрес <b>куда</b>:",
        "en": "🏁 Choose <b>destination</b> address:",
    },
    "trip_ask_start_km": {
        "de": "📊 <b>Kilometerstand zu Beginn</b> eingeben (km):",
        "ua": "📊 Введіть <b>пробіг на початку</b> поїздки (км):",
        "ru": "📊 Введите <b>пробег в начале</b> поездки (км):",
        "en": "📊 Enter <b>mileage at start</b> of trip (km):",
    },
    "trip_ask_end_km": {
        "de": "📊 <b>Kilometerstand am Ende</b> eingeben (km):",
        "ua": "📊 Введіть <b>пробіг наприкінці</b> поїздки (км):",
        "ru": "📊 Введите <b>пробег в конце</b> поездки (км):",
        "en": "📊 Enter <b>mileage at end</b> of trip (km):",
    },
    "trip_ask_purpose": {
        "de": "💼 <b>Fahrtgrund</b> wählen:",
        "ua": "💼 Оберіть <b>мету поїздки</b>:",
        "ru": "💼 Выберите <b>цель поездки</b>:",
        "en": "💼 Choose <b>trip purpose</b>:",
    },
    "trip_ask_notes": {
        "de": "📝 Anmerkungen hinzufügen (oder '-' überspringen):",
        "ua": "📝 Додайте примітки (або '-' щоб пропустити):",
        "ru": "📝 Добавьте примечания (или '-' чтобы пропустить):",
        "en": "📝 Add notes (or '-' to skip):",
    },
    "trip_edit_what": {
        "de": "✏️ Was möchten Sie bearbeiten?",
        "ua": "✏️ Що бажаєте змінити?",
        "ru": "✏️ Что хотите изменить?",
        "en": "✏️ What would you like to edit?",
    },
    "trip_mileage_error": {
        "de": "⚠️ Endkilometerstand kann nicht kleiner als Startkilometerstand sein.",
        "ua": "⚠️ Кінцевий пробіг не може бути менший за початковий.",
        "ru": "⚠️ Конечный пробег не может быть меньше начального.",
        "en": "⚠️ End mileage cannot be less than start mileage.",
    },

    # ── Трекінг ───────────────────────────────────────────────────────────────
    "track_active_already": {
        "de": "📡 Tracking läuft bereits!\n\nSenden Sie Ihren Live-Standort – der Bot verfolgt Ihre Fahrten automatisch.\nBeenden: /stoptrack",
        "ua": "📡 Трекінг вже активний!\n\nНадсилайте live-геолокацію — бот фіксує поїздки автоматично.\nЗупинити: /stoptrack",
        "ru": "📡 Трекинг уже активен!\n\nОтправляйте live-геолокацию — бот фиксирует поездки автоматически.\nОстановить: /stoptrack",
        "en": "📡 Tracking already active!\n\nSend your live location – the bot tracks trips automatically.\nStop: /stoptrack",
    },
    "track_started": {
        "de": "✅ Tracking gestartet — <b>{vehicle}</b>\n📊 Aktueller km-Stand: <b>{km:,} km</b>\n\n📡 Bitte <b>Live-Standort</b> senden:\n<i>📎 Büroklammer → Standort → Live-Standort teilen</i>\n\nDer Bot registriert jeden Stopp ≥ 1 Minute automatisch.\nTracking beenden: /stoptrack",
        "ua": "✅ Трекінг активовано — <b>{vehicle}</b>\n📊 Пробіг зараз: <b>{km:,} км</b>\n\n📡 Тепер надішліть <b>Live Location</b>:\n<i>📎 Скріпка → Геолокація → Поділитися live-геолокацією</i>\n\nБот автоматично фіксує кожну зупинку ≥ 1 хв.\nЗупинити трекінг: /stoptrack",
        "ru": "✅ Трекинг активирован — <b>{vehicle}</b>\n📊 Пробег сейчас: <b>{km:,} км</b>\n\n📡 Теперь отправьте <b>Live Location</b>:\n<i>📎 Скрепка → Геолокация → Поделиться live-геолокацией</i>\n\nБот автоматически фиксирует каждую остановку ≥ 1 мин.\nОстановить трекинг: /stoptrack",
        "en": "✅ Tracking activated — <b>{vehicle}</b>\n📊 Current mileage: <b>{km:,} km</b>\n\n📡 Now send your <b>Live Location</b>:\n<i>📎 Paperclip → Location → Share live location</i>\n\nThe bot automatically records every stop ≥ 1 min.\nStop tracking: /stoptrack",
    },
    "track_arrival_known": {
        "de": "📍 <b>Ankunft registriert</b>\n📌 {label} ({type})\n📏 +{km} km  |  Tacho: {odometer:,} km\n<i>Zweck: geschäftlich — ändern /trips</i>",
        "ua": "📍 <b>Прибуття зафіксовано</b>\n📌 {label} ({type})\n📏 +{km} км  |  Одометр: {odometer:,} км\n<i>Мета: geschäftlich — змінити /trips</i>",
        "ru": "📍 <b>Прибытие зафиксировано</b>\n📌 {label} ({type})\n📏 +{km} км  |  Одометр: {odometer:,} км\n<i>Цель: geschäftlich — изменить /trips</i>",
        "en": "📍 <b>Arrival recorded</b>\n📌 {label} ({type})\n📏 +{km} km  |  Odometer: {odometer:,} km\n<i>Purpose: business — change via /trips</i>",
    },
    "track_arrival_unknown": {
        "de": "❓ <b>Neuer Stopp!</b>\n<code>{addr}</code>\n\n📏 +{km} km\n\nFahrtgrund?",
        "ua": "❓ <b>Нова зупинка!</b>\n<code>{addr}</code>\n\n📏 +{km} км\n\nМета поїздки?",
        "ru": "❓ <b>Новая остановка!</b>\n<code>{addr}</code>\n\n📏 +{km} км\n\nЦель поездки?",
        "en": "❓ <b>New stop!</b>\n<code>{addr}</code>\n\n📏 +{km} km\n\nTrip purpose?",
    },
    "track_save_addr": {
        "de": "Diesen Ort für zukünftige Fahrten speichern?",
        "ua": "Зберегти це місце для майбутніх поїздок?",
        "ru": "Сохранить это место для будущих поездок?",
        "en": "Save this location for future trips?",
    },
    "track_ask_label": {
        "de": "Name für diesen Ort eingeben:",
        "ua": "Введіть назву для цього місця:",
        "ru": "Введите название для этого места:",
        "en": "Enter a name for this location:",
    },
    "track_trip_saved": {
        "de": "✅ Fahrt gespeichert. 📏 +{km} km",
        "ua": "✅ Поїздку записано. 📏 +{km} км",
        "ru": "✅ Поездка записана. 📏 +{km} км",
        "en": "✅ Trip saved. 📏 +{km} km",
    },
    "track_stopped": {
        "de": "🏁 <b>Tracking beendet</b>\n\n⏱ Dauer: {h}h {m}min\n📋 Fahrten: <b>{trips}</b>\n📏 Gesamtstrecke: <b>{total} km</b>\n  💼 Geschäftlich: {biz} km\n  🏠 Privat: {priv} km\n\nFahrtenbuch: /trips\nPDF-Bericht: /report",
        "ua": "🏁 <b>Трекінг завершено</b>\n\n⏱ Тривалість: {h}г {m}хв\n📋 Поїздок: <b>{trips}</b>\n📏 Загальний пробіг: <b>{total} км</b>\n  💼 Ділових: {biz} км\n  🏠 Приватних: {priv} км\n\nЖурнал: /trips\nPDF-звіт: /report",
        "ru": "🏁 <b>Трекинг завершён</b>\n\n⏱ Длительность: {h}ч {m}мин\n📋 Поездок: <b>{trips}</b>\n📏 Общий пробег: <b>{total} км</b>\n  💼 Деловых: {biz} км\n  🏠 Частных: {priv} км\n\nЖурнал: /trips\nPDF-отчёт: /report",
        "en": "🏁 <b>Tracking stopped</b>\n\n⏱ Duration: {h}h {m}min\n📋 Trips: <b>{trips}</b>\n📏 Total distance: <b>{total} km</b>\n  💼 Business: {biz} km\n  🏠 Private: {priv} km\n\nLog: /trips\nPDF report: /report",
    },
    "track_no_session": {
        "de": "ℹ️ Kein aktives Tracking. Starten mit /track",
        "ua": "ℹ️ Трекінг не активний. Запустити: /track",
        "ru": "ℹ️ Трекинг не активен. Запустить: /track",
        "en": "ℹ️ No active tracking. Start with /track",
    },
    "track_status": {
        "de": "📡 <b>Tracking aktiv</b>\n\n⏱ Dauer: {h}h {m}min\n📍 GPS-Punkte: {pts}\n📏 Gespeichert: {km} km\n\nBeenden: /stoptrack",
        "ua": "📡 <b>Трекінг активний</b>\n\n⏱ Тривалість: {h}г {m}хв\n📍 GPS-точок: {pts}\n📏 Накопичено: {km} км\n\nЗупинити: /stoptrack",
        "ru": "📡 <b>Трекинг активен</b>\n\n⏱ Длительность: {h}ч {m}мин\n📍 GPS-точек: {pts}\n📏 Накоплено: {km} км\n\nОстановить: /stoptrack",
        "en": "📡 <b>Tracking active</b>\n\n⏱ Duration: {h}h {m}min\n📍 GPS points: {pts}\n📏 Accumulated: {km} km\n\nStop: /stoptrack",
    },

    # ── Звіт ─────────────────────────────────────────────────────────────────
    "report_title": {
        "de": "📄 <b>Fahrtenbuch PDF generieren</b>\n\nFahrzeug wählen:",
        "ua": "📄 <b>Генерація Fahrtenbuch PDF</b>\n\nОберіть автомобіль:",
        "ru": "📄 <b>Генерация Fahrtenbuch PDF</b>\n\nВыберите автомобиль:",
        "en": "📄 <b>Generate Fahrtenbuch PDF</b>\n\nChoose vehicle:",
    },
    "report_period": {
        "de": "📅 Zeitraum wählen:",
        "ua": "📅 Оберіть період:",
        "ru": "📅 Выберите период:",
        "en": "📅 Choose period:",
    },
    "report_generating": {
        "de": "⏳ Bericht für <b>{period}</b> wird erstellt…",
        "ua": "⏳ Генерую звіт за <b>{period}</b>…",
        "ru": "⏳ Генерирую отчёт за <b>{period}</b>…",
        "en": "⏳ Generating report for <b>{period}</b>…",
    },
    "report_empty": {
        "de": "📋 Für den angegebenen Zeitraum wurden keine Fahrten gefunden.",
        "ua": "📋 За вказаний період поїздок не знайдено.",
        "ru": "📋 За указанный период поездок не найдено.",
        "en": "📋 No trips found for the specified period.",
    },
    "report_caption": {
        "de": "📄 <b>Fahrtenbuch</b> — {period}\n🚗 {vehicle}\n📊 Fahrten: {trips} | Gesamtstrecke: <b>{km} km</b>",
        "ua": "📄 <b>Fahrtenbuch</b> — {period}\n🚗 {vehicle}\n📊 Поїздок: {trips} | Загальний пробіг: <b>{km} км</b>",
        "ru": "📄 <b>Fahrtenbuch</b> — {period}\n🚗 {vehicle}\n📊 Поездок: {trips} | Общий пробег: <b>{km} км</b>",
        "en": "📄 <b>Fahrtenbuch</b> — {period}\n🚗 {vehicle}\n📊 Trips: {trips} | Total mileage: <b>{km} km</b>",
    },
    "report_date_from": {
        "de": "Startdatum eingeben (TT.MM.JJJJ):",
        "ua": "Введіть дату <b>початку</b> (ДД.ММ.РРРР):",
        "ru": "Введите дату <b>начала</b> (ДД.ММ.ГГГГ):",
        "en": "Enter <b>start</b> date (DD.MM.YYYY):",
    },
    "report_date_to": {
        "de": "Enddatum eingeben (TT.MM.JJJJ):",
        "ua": "Введіть дату <b>кінця</b> (ДД.ММ.РРРР):",
        "ru": "Введите дату <b>конца</b> (ДД.ММ.ГГГГ):",
        "en": "Enter <b>end</b> date (DD.MM.YYYY):",
    },

    # ── Налаштування ──────────────────────────────────────────────────────────
    "settings_title": {
        "de": "⚙️ <b>Einstellungen</b>\n\n👤 Name: <b>{name}</b>\n🌐 Sprache: <b>{lang_label}</b>\n📡 Geofence-Radius: <b>{radius} m</b>\n🆔 Telegram ID: <code>{tg_id}</code>",
        "ua": "⚙️ <b>Налаштування</b>\n\n👤 Ім'я: <b>{name}</b>\n🌐 Мова: <b>{lang_label}</b>\n📡 Радіус геофенсу: <b>{radius} м</b>\n🆔 Telegram ID: <code>{tg_id}</code>",
        "ru": "⚙️ <b>Настройки</b>\n\n👤 Имя: <b>{name}</b>\n🌐 Язык: <b>{lang_label}</b>\n📡 Радиус геофенса: <b>{radius} м</b>\n🆔 Telegram ID: <code>{tg_id}</code>",
        "en": "⚙️ <b>Settings</b>\n\n👤 Name: <b>{name}</b>\n🌐 Language: <b>{lang_label}</b>\n📡 Geofence radius: <b>{radius} m</b>\n🆔 Telegram ID: <code>{tg_id}</code>",
    },
    "settings_name": {
        "de": "✏️ Name ändern",
        "ua": "✏️ Змінити ім'я",
        "ru": "✏️ Изменить имя",
        "en": "✏️ Change name",
    },
    "settings_lang": {
        "de": "🌐 Sprache ändern",
        "ua": "🌐 Змінити мову",
        "ru": "🌐 Изменить язык",
        "en": "🌐 Change language",
    },
    "settings_home": {
        "de": "🏠 Heimatadresse",
        "ua": "🏠 Домашня адреса",
        "ru": "🏠 Домашний адрес",
        "en": "🏠 Home address",
    },
    "settings_radius": {
        "de": "📡 Geofence-Radius",
        "ua": "📡 Радіус геофенсингу",
        "ru": "📡 Радиус геофенсинга",
        "en": "📡 Geofence radius",
    },
    "settings_ask_name": {
        "de": "Neuen Namen eingeben:",
        "ua": "Введіть нове ім'я:",
        "ru": "Введите новое имя:",
        "en": "Enter new name:",
    },
    "settings_name_changed": {
        "de": "✅ Name geändert: <b>{name}</b>",
        "ua": "✅ Ім'я змінено на <b>{name}</b>",
        "ru": "✅ Имя изменено на <b>{name}</b>",
        "en": "✅ Name changed to <b>{name}</b>",
    },
    "settings_lang_changed": {
        "de": "✅ Sprache geändert: <b>{lang}</b>",
        "ua": "✅ Мову змінено: <b>{lang}</b>",
        "ru": "✅ Язык изменён: <b>{lang}</b>",
        "en": "✅ Language changed: <b>{lang}</b>",
    },
    "settings_radius_ask": {
        "de": "📡 Geofence-Radius wählen\n<i>(Entfernung zur automatischen Adresserkennung)</i>",
        "ua": "📡 Оберіть радіус геофенсингу\n<i>(відстань для автоматичного визначення адреси)</i>",
        "ru": "📡 Выберите радиус геофенсинга\n<i>(расстояние для автоматического определения адреса)</i>",
        "en": "📡 Choose geofence radius\n<i>(distance for automatic address detection)</i>",
    },
    "settings_radius_changed": {
        "de": "✅ Geofence-Radius: <b>{radius} m</b>",
        "ua": "✅ Радіус геофенсингу: <b>{radius} м</b>",
        "ru": "✅ Радиус геофенсинга: <b>{radius} м</b>",
        "en": "✅ Geofence radius: <b>{radius} m</b>",
    },
    "settings_home_ask": {
        "de": "🏠 Heimatadresse wählen:",
        "ua": "🏠 Оберіть домашню адресу:",
        "ru": "🏠 Выберите домашний адрес:",
        "en": "🏠 Choose home address:",
    },
    "settings_home_changed": {
        "de": "✅ Heimatadresse: <b>{label}</b>",
        "ua": "✅ Домашня адреса: <b>{label}</b>",
        "ru": "✅ Домашний адрес: <b>{label}</b>",
        "en": "✅ Home address: <b>{label}</b>",
    },

    # ── Нагадування (scheduler) ───────────────────────────────────────────────
    "remind_monthly": {
        "de": "📅 <b>Erinnerung: Fahrtenbuch</b>\n\nDer Monat <b>{month}</b> ist vorbei.\nZeit, den PDF-Bericht für das Finanzamt zu erstellen!\n\n➡️ /report",
        "ua": "📅 <b>Нагадування: Fahrtenbuch</b>\n\nМісяць <b>{month}</b> завершився.\nЧас згенерувати PDF-звіт для Finanzamt!\n\n➡️ /report",
        "ru": "📅 <b>Напоминание: Fahrtenbuch</b>\n\nМесяц <b>{month}</b> завершился.\nВремя сгенерировать PDF-отчёт для Finanzamt!\n\n➡️ /report",
        "en": "📅 <b>Reminder: Fahrtenbuch</b>\n\nMonth <b>{month}</b> is over.\nTime to generate the PDF report for the Finanzamt!\n\n➡️ /report",
    },
    "remind_inactive": {
        "de": "💡 <b>Erinnerung</b>\n\nSeit mehr als 5 Tagen keine Fahrten eingetragen.\nBitte halten Sie Ihr Fahrtenbuch aktuell!\n\n➕ Fahrt hinzufügen: /newtrip\n📡 GPS-Tracking: /track",
        "ua": "💡 <b>Нагадування</b>\n\nВи не додавали поїздок більше 5 днів.\nНе забудьте вести Fahrtenbuch актуальним!\n\n➕ Додати поїздку: /newtrip\n📡 GPS-трекінг: /track",
        "ru": "💡 <b>Напоминание</b>\n\nВы не добавляли поездки более 5 дней.\nНе забывайте вести Fahrtenbuch актуальным!\n\n➕ Добавить поездку: /newtrip\n📡 GPS-трекинг: /track",
        "en": "💡 <b>Reminder</b>\n\nNo trips added for more than 5 days.\nPlease keep your Fahrtenbuch up to date!\n\n➕ Add trip: /newtrip\n📡 GPS tracking: /track",
    },

    # ── Статистика ────────────────────────────────────────────────────────────
    "stats_title": {
        "de": "📊 <b>Fahrtstatistik</b>",
        "ua": "📊 <b>Статистика поїздок</b>",
        "ru": "📊 <b>Статистика поездок</b>",
        "en": "📊 <b>Trip Statistics</b>",
    },
    "stats_empty": {
        "de": "📊 Keine Statistik — noch keine Fahrten.",
        "ua": "📊 Статистика порожня — поїздок ще немає.",
        "ru": "📊 Статистика пуста — поездок ещё нет.",
        "en": "📊 No statistics — no trips yet.",
    },
    "stats_chart_title": {
        "de": "📈 Kilometerdiagramm — letzte 8 Wochen",
        "ua": "📈 Діаграма км — останні 8 тижнів",
        "ru": "📈 График км — последние 8 недель",
        "en": "📈 Mileage chart — last 8 weeks",
    },

    # ── Backup ────────────────────────────────────────────────────────────────
    "backup_done": {
        "de": "✅ Datenbank-Backup erstellt.",
        "ua": "✅ Резервну копію БД створено.",
        "ru": "✅ Резервная копия БД создана.",
        "en": "✅ Database backup created.",
    },
    "backup_no_access": {
        "de": "⛔ Kein Zugriff.",
        "ua": "⛔ Немає доступу.",
        "ru": "⛔ Нет доступа.",
        "en": "⛔ Access denied.",
    },


    # ── Меню (нові кнопки) ───────────────────────────────────────────────────
    "menu_receipts": {
        "de": "🧾 Belege",
        "ua": "🧾 Чеки",
        "ru": "🧾 Чеки",
        "en": "🧾 Receipts",
    },
    "menu_tax": {
        "de": "💰 EÜR Bericht",
        "ua": "💰 EÜR Звіт",
        "ru": "💰 EÜR Отчёт",
        "en": "💰 EÜR Report",
    },

    # ── Чеки ─────────────────────────────────────────────────────────────────
    "receipt_send_photo": {
        "de": "📸 Senden Sie einfach ein Foto Ihres Kassenbons — der Bot erkennt es automatisch!",
        "ua": "📸 Просто надішліть фото чека — бот розпізнає його автоматично!",
        "ru": "📸 Просто отправьте фото чека — бот распознает его автоматически!",
        "en": "📸 Just send a photo of your receipt — the bot recognizes it automatically!",
    },
    "receipt_hint": {
        "de": "Oder /newreceipt für manuelle Eingabe.",
        "ua": "Або /newreceipt для ручного введення.",
        "ru": "Или /newreceipt для ручного ввода.",
        "en": "Or /newreceipt for manual entry.",
    },

    # ── Доходи ───────────────────────────────────────────────────────────────
    "menu_incomes": {
        "de": "💶 Einnahmen",
        "ua": "💶 Доходи",
        "ru": "💶 Доходы",
        "en": "💶 Income",
    },
    "income_added": {
        "de": "✅ <b>Einnahme gespeichert!</b>",
        "ua": "✅ <b>Дохід записано!</b>",
        "ru": "✅ <b>Доход записан!</b>",
        "en": "✅ <b>Income saved!</b>",
    },
    "income_deleted": {
        "de": "✅ Einnahme gelöscht.",
        "ua": "✅ Дохід видалено.",
        "ru": "✅ Доход удалён.",
        "en": "✅ Income deleted.",
    },

    # ── Експорт ───────────────────────────────────────────────────────────────
    "export_title": {
        "de": "📤 <b>Datenexport (CSV)</b>",
        "ua": "📤 <b>Експорт даних (CSV)</b>",
        "ru": "📤 <b>Экспорт данных (CSV)</b>",
        "en": "📤 <b>Data Export (CSV)</b>",
    },

    # ── Помилки ───────────────────────────────────────────────────────────────
    "not_found": {
        "de": "Nicht gefunden.",
        "ua": "Не знайдено.",
        "ru": "Не найдено.",
        "en": "Not found.",
    },
    "no_vehicles": {
        "de": "⚠️ Zuerst ein Fahrzeug hinzufügen: /cars",
        "ua": "⚠️ Спочатку додайте авто в /cars",
        "ru": "⚠️ Сначала добавьте авто в /cars",
        "en": "⚠️ First add a vehicle: /cars",
    },
    "date_format_error": {
        "de": "⚠️ Falsches Format. Datum als TT.MM.JJJJ oder 'heute' eingeben:",
        "ua": "⚠️ Невірний формат. Введіть дату як ДД.ММ.РРРР або 'сьогодні':",
        "ru": "⚠️ Неверный формат. Введите дату как ДД.ММ.ГГГГ или 'сегодня':",
        "en": "⚠️ Wrong format. Enter date as DD.MM.YYYY or 'today':",
    },
    "main_menu": {
        "de": "Hauptmenü:",
        "ua": "Головне меню:",
        "ru": "Главное меню:",
        "en": "Main menu:",
    },
    "manual_input": {
        "de": "✍️ Manuell eingeben",
        "ua": "✍️ Ввести вручну",
        "ru": "✍️ Ввести вручную",
        "en": "✍️ Enter manually",
    },
    "add_address": {
        "de": "➕ Adresse hinzufügen",
        "ua": "➕ Додати адресу",
        "ru": "➕ Добавить адрес",
        "en": "➕ Add address",
    },
    "import_csv": {
        "de": "📂 CSV importieren",
        "ua": "📂 Імпорт CSV",
        "ru": "📂 Импорт CSV",
        "en": "📂 Import CSV",
    },
}


def t(key: str, locale: str = "de", **kwargs) -> str:
    """
    Повертає переклад для ключа і мови.
    Підтримує форматування: t("welcome_back", locale="ua", name="Max")
    """
    lang = locale if locale in SUPPORTED_LANGS else "de"
    entry = _TRANSLATIONS.get(key, {})
    text = entry.get(lang) or entry.get("de") or f"[{key}]"
    if kwargs:
        try:
            text = text.format(**kwargs)
        except (KeyError, ValueError):
            pass
    return text


def get_translator(lang: str):
    """Повертає функцію-перекладач прив'язану до конкретної мови."""
    def _t(key: str, **kwargs) -> str:
        return t(key, locale=lang, **kwargs)
    return _t
