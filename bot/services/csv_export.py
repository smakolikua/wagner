"""
csv_export.py — експорт даних у CSV для бухгалтера / DATEV / Excel.

Формати:
  - receipts_export: всі чеки з категоріями, ПДВ, датою
  - trips_export: всі поїздки з пробігом і метою
  - income_export: всі доходи з клієнтом і рахунком
  - full_export: всі три в одному ZIP-архіві
"""
import csv
import io
import zipfile
from datetime import date
from typing import List
from ..models import Receipt, Trip, Income, TripPurpose


def _csv_bytes(rows: list[list], headers: list[str]) -> bytes:
    """Генерує UTF-8 CSV з BOM (для коректного відкриття в Excel)."""
    buf = io.StringIO()
    writer = csv.writer(buf, delimiter=";", quoting=csv.QUOTE_MINIMAL)
    writer.writerow(headers)
    writer.writerows(rows)
    # BOM + UTF-8 для Excel
    return "\ufeff".encode("utf-8") + buf.getvalue().encode("utf-8")


def export_receipts_csv(receipts: List[Receipt]) -> bytes:
    headers = [
        "Datum", "Lieferant", "Brutto (€)", "Netto (€)", "MwSt (€)",
        "MwSt-Satz (%)", "Kategorie", "Beschreibung", "Typ", "Belegnummer",
    ]
    rows = []
    for r in sorted(receipts, key=lambda x: x.date):
        rows.append([
            r.date.strftime("%d.%m.%Y"),
            r.vendor or "",
            f"{r.amount_gross:.2f}",
            f"{r.net_amount:.2f}",
            f"{r.vat_amount or 0:.2f}",
            str(r.vat_rate),
            r.category.name if r.category else "",
            r.description or "",
            "geschäftlich" if r.is_business else "privat",
            str(r.id),
        ])
    return _csv_bytes(rows, headers)


def export_trips_csv(trips: List[Trip]) -> bytes:
    headers = [
        "Datum", "Fahrzeug", "Abfahrt", "Ziel",
        "km Start", "km Ende", "km gesamt", "Zweck", "Anmerkungen",
    ]
    rows = []
    for tr in sorted(trips, key=lambda x: x.date):
        vehicle_name = tr.vehicle.display_name if tr.vehicle else ""
        rows.append([
            tr.date.strftime("%d.%m.%Y"),
            vehicle_name,
            tr.start_label,
            tr.end_label,
            f"{tr.start_mileage:.0f}",
            f"{tr.end_mileage:.0f}",
            f"{tr.distance:.1f}",
            tr.purpose.value,
            tr.notes or "",
        ])
    return _csv_bytes(rows, headers)


def export_income_csv(incomes: List[Income]) -> bytes:
    headers = [
        "Datum", "Kunde", "Rechnungsnummer",
        "Netto (€)", "MwSt-Satz (%)", "MwSt (€)", "Brutto (€)",
        "Beschreibung", "Kleinunternehmer",
    ]
    rows = []
    for inc in sorted(incomes, key=lambda x: x.date):
        rows.append([
            inc.date.strftime("%d.%m.%Y"),
            inc.client_name or "",
            inc.invoice_number or "",
            f"{inc.amount:.2f}",
            str(inc.vat_rate),
            f"{inc.vat_amount:.2f}",
            f"{inc.gross_amount:.2f}",
            inc.description or "",
            "Ja" if inc.is_kleinunternehmer else "Nein",
        ])
    return _csv_bytes(rows, headers)


def export_full_zip(
    receipts: List[Receipt],
    trips: List[Trip],
    incomes: List[Income],
    period_label: str,
) -> bytes:
    """Всі три CSV у ZIP-архіві."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        safe = period_label.replace(" ", "_").replace("/", "-")
        if receipts:
            zf.writestr(f"Belege_{safe}.csv",  export_receipts_csv(receipts))
        if trips:
            zf.writestr(f"Fahrten_{safe}.csv", export_trips_csv(trips))
        if incomes:
            zf.writestr(f"Einnahmen_{safe}.csv", export_income_csv(incomes))
        # README
        readme = (
            f"Fahrtenbuch Bot — Export {period_label}\n"
            f"Erstellt: {date.today().strftime('%d.%m.%Y')}\n\n"
            f"Dateien:\n"
            f"  Belege_{safe}.csv     — Betriebsausgaben (Receipts)\n"
            f"  Fahrten_{safe}.csv    — Fahrtenbuch (Trips)\n"
            f"  Einnahmen_{safe}.csv  — Einnahmen (Income)\n\n"
            f"Format: CSV, Trennzeichen Semikolon (;), Encoding UTF-8 mit BOM\n"
            f"Kompatibel mit: Excel, DATEV, Lexware, LibreOffice Calc\n"
        )
        zf.writestr("README.txt", readme)
    return buf.getvalue()
