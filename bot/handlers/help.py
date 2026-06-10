"""help.py — /help handler з підтримкою 4 мов."""
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from ..models import User
from ..i18n import t

router = Router(name="help")

_HELP = {
    "de": """📖 <b>Fahrtenbuch Bot — Hilfe</b>

<b>Fahrzeuge</b>
/cars — Liste, hinzufügen, bearbeiten, löschen
  • Mehrere Fahrzeuge möglich
  • Kilometerstand wird bei jeder Fahrt aktualisiert

<b>Adressen</b>
/addresses — Gespeicherte Adressen verwalten
  • Typen: Heimatadresse / Kunde / Büro / Sonstiges
  • CSV-Import: Format <code>name,address,type</code>
  • Geocodierung erfolgt automatisch

<b>Fahrten</b>
/trips — Fahrtenbuch mit Monatsfilter
/newtrip — Fahrt manuell hinzufügen

<b>GPS-Tracking</b>
/track — Automatisches Tracking starten
  1. Fahrzeug wählen
  2. Live-Standort senden (📎 → Standort → Live)
  3. Bot registriert Stopps ≥ 1 Min. automatisch
/stoptrack — Tracking beenden, Zusammenfassung
/trackstatus — Status der aktiven Sitzung

<b>Berichte</b>
/report — PDF Fahrtenbuch erstellen
  • Monat / Quartal / beliebiger Zeitraum

<b>Einstellungen</b>
/settings — Sprache

<b>Belege & Steuern</b>
/receipts — Belege verwalten (oder Foto senden)
/newreceipt — Beleg manuell hinzufügen
/incomes — Einnahmen verwalten
/addincome — Einnahme hinzufügen
/taxreport — EÜR PDF erstellen
/export — CSV-Export für DATEV/Buchhalter, Heimatadresse, Geofence-Radius

<b>CSV-Format für Adressimport:</b>
<pre>name,address,type
Heimat,Musterstr 1 München,Heimatadresse
Kunde GmbH,Hauptstr 5 Berlin,Kunde</pre>""",

    "ua": """📖 <b>Fahrtenbuch Bot — Довідка</b>

<b>Автомобілі</b>
/cars — Список, додавання, редагування, видалення
  • Можна мати кілька авто
  • Пробіг оновлюється автоматично

<b>Адреси</b>
/addresses — Керування збереженими адресами
  • Типи: Heimatadresse / Kunde / Büro / Sonstiges
  • CSV-імпорт: формат <code>name,address,type</code>
  • Геокодування відбувається автоматично

<b>Поїздки</b>
/trips — Журнал поїздок з фільтром по місяцях
/newtrip — Додати поїздку вручну

<b>GPS-трекінг</b>
/track — Почати автоматичний трекінг
  1. Оберіть авто
  2. Надішліть Live Location (📎 → Геолокація → live)
  3. Бот фіксує зупинки ≥ 1 хв автоматично
/stoptrack — Зупинити, отримати підсумок
/trackstatus — Статус активної сесії

<b>Звіти</b>
/report — Згенерувати PDF Fahrtenbuch
  • Місяць / квартал / довільний діапазон

<b>Налаштування</b>
/settings — Мова

<b>Чеки та податки</b>
/receipts — Керування чеками (або надішліть фото)
/newreceipt — Додати чек вручну
/incomes — Керування доходами
/addincome — Додати дохід
/taxreport — Згенерувати EÜR PDF
/export — Експорт CSV для бухгалтера, домашня адреса, радіус геофенсингу

<b>CSV-формат для імпорту адрес:</b>
<pre>name,address,type
Heimat,Musterstr 1 München,Heimatadresse
Kunde GmbH,Hauptstr 5 Berlin,Kunde</pre>""",

    "ru": """📖 <b>Fahrtenbuch Bot — Справка</b>

<b>Автомобили</b>
/cars — Список, добавление, редактирование, удаление
  • Можно иметь несколько авто
  • Пробег обновляется автоматически

<b>Адреса</b>
/addresses — Управление сохранёнными адресами
  • Типы: Heimatadresse / Kunde / Büro / Sonstiges
  • CSV-импорт: формат <code>name,address,type</code>
  • Геокодирование происходит автоматически

<b>Поездки</b>
/trips — Журнал поездок с фильтром по месяцам
/newtrip — Добавить поездку вручную

<b>GPS-трекинг</b>
/track — Начать автоматический трекинг
  1. Выберите авто
  2. Отправьте Live Location (📎 → Геолокация → live)
  3. Бот фиксирует остановки ≥ 1 мин автоматически
/stoptrack — Остановить, получить итог
/trackstatus — Статус активной сессии

<b>Отчёты</b>
/report — Сгенерировать PDF Fahrtenbuch
  • Месяц / квартал / произвольный диапазон

<b>Настройки</b>
/settings — Язык

<b>Чеки и налоги</b>
/receipts — Управление чеками (или отправьте фото)
/newreceipt — Добавить чек вручную
/incomes — Управление доходами
/addincome — Добавить доход
/taxreport — Сгенерировать EÜR PDF
/export — Экспорт CSV для бухгалтера, домашний адрес, радиус геофенсинга

<b>CSV-формат для импорта адресов:</b>
<pre>name,address,type
Heimat,Musterstr 1 München,Heimatadresse
Kunde GmbH,Hauptstr 5 Berlin,Kunde</pre>""",

    "en": """📖 <b>Fahrtenbuch Bot — Help</b>

<b>Vehicles</b>
/cars — List, add, edit, delete
  • Multiple vehicles supported
  • Mileage updates automatically with each trip

<b>Addresses</b>
/addresses — Manage saved addresses
  • Types: Heimatadresse / Kunde / Büro / Sonstiges
  • CSV import: format <code>name,address,type</code>
  • Geocoding happens automatically

<b>Trips</b>
/trips — Trip log with month filter
/newtrip — Add a trip manually

<b>GPS Tracking</b>
/track — Start automatic tracking
  1. Choose your vehicle
  2. Send Live Location (📎 → Location → Live)
  3. Bot records stops ≥ 1 min automatically
/stoptrack — Stop tracking, get summary
/trackstatus — Status of active session

<b>Reports</b>
/report — Generate PDF Fahrtenbuch
  • Month / quarter / custom date range

<b>Settings</b>
/settings — Language

<b>Receipts & Taxes</b>
/receipts — Manage receipts (or send a photo)
/newreceipt — Add receipt manually
/incomes — Manage income
/addincome — Add income entry
/taxreport — Generate EÜR PDF
/export — CSV export for accountant, home address, geofence radius

<b>CSV format for address import:</b>
<pre>name,address,type
Heimat,Musterstr 1 München,Heimatadresse
Kunde GmbH,Hauptstr 5 Berlin,Kunde</pre>""",
}


@router.message(Command("help"))
async def cmd_help(message: Message, user: User):
    lang = user.lang if user else "de"
    text = _HELP.get(lang, _HELP["de"])
    await message.answer(text, parse_mode="HTML")
