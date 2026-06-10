import csv
import io
from typing import List, Tuple
from loguru import logger
from ..models import AddressType
from .geo import geocode_address


async def parse_addresses_csv(
    content: bytes,
) -> Tuple[List[dict], List[str]]:
    """
    Парсить CSV-файл з адресами.

    Очікуваний формат (з заголовком):
        name,address,type
        Kunde Müller,Hauptstraße 1 München,Kunde
        Büro Berlin,Unter den Linden 5 Berlin,Büro

    Повертає:
        (список готових dict-ів, список помилок)
    """
    results = []
    errors = []

    try:
        text = content.decode("utf-8-sig")  # utf-8-sig обробляє BOM
    except UnicodeDecodeError:
        try:
            text = content.decode("latin-1")
        except Exception as e:
            return [], [f"Не вдалося розкодувати файл: {e}"]

    reader = csv.DictReader(io.StringIO(text))

    # Нормалізуємо fieldnames (прибираємо BOM що залишається у першому полі)
    if reader.fieldnames:
        reader.fieldnames = [f.lstrip("\ufeff").strip() for f in reader.fieldnames]

    # Перевіряємо заголовки
    if reader.fieldnames is None:
        return [], ["Файл порожній або не є CSV"]

    required = {"name", "address"}
    fieldnames_lower = {f.lower().strip() for f in reader.fieldnames}
    if not required.issubset(fieldnames_lower):
        return [], [f"CSV має містити колонки: name, address (та опціонально type). Знайдено: {', '.join(reader.fieldnames)}"]

    for i, row in enumerate(reader, start=2):
        # Нормалізуємо ключі
        row = {k.lower().strip(): v.strip() for k, v in row.items()}

        name = row.get("name", "").strip()
        address = row.get("address", "").strip()
        type_str = row.get("type", "Sonstiges").strip()

        if not name:
            errors.append(f"Рядок {i}: пуста колонка 'name'")
            continue
        if not address:
            errors.append(f"Рядок {i}: пуста колонка 'address'")
            continue

        # Маппінг типів (підтримуємо різні варіанти написання)
        type_map = {
            "heimatadresse": AddressType.HOME,
            "home": AddressType.HOME,
            "kunde": AddressType.CLIENT,
            "client": AddressType.CLIENT,
            "klient": AddressType.CLIENT,
            "büro": AddressType.OFFICE,
            "buro": AddressType.OFFICE,
            "buero": AddressType.OFFICE,
            "büro ": AddressType.OFFICE,
            "office": AddressType.OFFICE,
            "sonstiges": AddressType.OTHER,
            "other": AddressType.OTHER,
            "інше": AddressType.OTHER,
        }
        addr_type = type_map.get(type_str.lower(), AddressType.OTHER)

        results.append({
            "label": name,
            "address_str": address,
            "type": addr_type,
        })

    return results, errors


async def geocode_batch(
    addresses: List[dict],
) -> Tuple[List[dict], List[str]]:
    """
    Геокодує пачку адрес. Повертає готові до збереження dict-и та помилки.
    """
    geocoded = []
    errors = []

    for item in addresses:
        coords = await geocode_address(item["address_str"])
        if coords:
            item["lat"], item["lon"] = coords
        else:
            errors.append(f"Не вдалося геокодувати: '{item['address_str']}'")
            item["lat"] = None
            item["lon"] = None
        geocoded.append(item)

    return geocoded, errors
