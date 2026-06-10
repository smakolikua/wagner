"""test_csv_export.py — тести CSV/ZIP експорту."""
import zipfile
import pytest
from datetime import date
from unittest.mock import MagicMock
from bot.services.csv_export import (
    export_receipts_csv, export_trips_csv,
    export_income_csv, export_full_zip,
)
from bot.models import Receipt, Trip, Income, TripPurpose


def _receipt(amount=59.50, vendor="REWE", biz=True, cat_name="Bürobedarf"):
    r = MagicMock(spec=Receipt)
    r.date = date(2025, 1, 15)
    r.amount_gross = amount
    r.net_amount = round(amount / 1.19, 2)
    r.vat_amount = round(amount - amount / 1.19, 2)
    r.vat_rate = 19
    r.vendor = vendor
    r.description = "Test receipt"
    r.is_business = biz
    r.category = MagicMock(); r.category.name = cat_name
    r.id = 1
    return r


def _trip(dist=45.0, biz=True):
    t = MagicMock(spec=Trip)
    t.date = date(2025, 1, 10)
    t.vehicle = MagicMock(); t.vehicle.display_name = "VW Golf (M-1)"
    t.start_label = "Heimat"; t.end_label = "Kunde"
    t.start_mileage = 85000.0; t.end_mileage = 85000 + dist
    t.distance = dist
    t.purpose = MagicMock()
    t.purpose.value = "geschäftlich" if biz else "privat"
    t.notes = None
    return t


def _income(amount=1500.0):
    i = MagicMock(spec=Income)
    i.date = date(2025, 1, 20)
    i.amount = amount
    i.vat_rate = 19
    i.vat_amount = round(amount * 0.19, 2)
    i.gross_amount = round(amount * 1.19, 2)
    i.client_name = "Müller GmbH"
    i.invoice_number = "2025-001"
    i.description = "Beratung"
    i.is_kleinunternehmer = False
    return i


class TestReceiptsCsv:
    def test_has_bom(self):
        csv = export_receipts_csv([_receipt()])
        assert csv[:3] == b'\xef\xbb\xbf'

    def test_semicolon_delimiter(self):
        csv = export_receipts_csv([_receipt()]).decode("utf-8-sig")
        assert ";" in csv

    def test_contains_vendor(self):
        csv = export_receipts_csv([_receipt(vendor="ALDI")]).decode("utf-8-sig")
        assert "ALDI" in csv

    def test_contains_amount(self):
        csv = export_receipts_csv([_receipt(amount=119.00)]).decode("utf-8-sig")
        assert "119" in csv

    def test_business_label(self):
        csv_biz  = export_receipts_csv([_receipt(biz=True)]).decode("utf-8-sig")
        csv_priv = export_receipts_csv([_receipt(biz=False)]).decode("utf-8-sig")
        assert "geschäftlich" in csv_biz
        assert "privat" in csv_priv

    def test_empty_list(self):
        csv = export_receipts_csv([])
        assert len(csv) > 0  # Хоча б заголовок


class TestTripsCsv:
    def test_contains_distance(self):
        csv = export_trips_csv([_trip(dist=45.5)]).decode("utf-8-sig")
        assert "45.5" in csv

    def test_contains_vehicle(self):
        csv = export_trips_csv([_trip()]).decode("utf-8-sig")
        assert "VW Golf" in csv

    def test_purpose_label(self):
        csv = export_trips_csv([_trip(biz=True)]).decode("utf-8-sig")
        assert "geschäftlich" in csv


class TestIncomeCsv:
    def test_contains_amount(self):
        csv = export_income_csv([_income(1500.0)]).decode("utf-8-sig")
        assert "1500" in csv

    def test_contains_client(self):
        csv = export_income_csv([_income()]).decode("utf-8-sig")
        assert "Müller" in csv

    def test_contains_invoice(self):
        csv = export_income_csv([_income()]).decode("utf-8-sig")
        assert "2025-001" in csv

    def test_kleinunternehmer_flag(self):
        inc = _income(); inc.is_kleinunternehmer = True
        csv = export_income_csv([inc]).decode("utf-8-sig")
        assert "Ja" in csv


class TestFullZip:
    def test_is_valid_zip(self):
        data = export_full_zip([_receipt()], [_trip()], [_income()], "Q1_2025")
        assert zipfile.is_zipfile(__import__("io").BytesIO(data))

    def test_zip_contains_all_files(self):
        data = export_full_zip([_receipt()], [_trip()], [_income()], "Q1_2025")
        with zipfile.ZipFile(__import__("io").BytesIO(data)) as zf:
            names = zf.namelist()
        assert any("Belege" in n for n in names)
        assert any("Fahrten" in n for n in names)
        assert any("Einnahmen" in n for n in names)
        assert any("README" in n for n in names)

    def test_zip_empty_data(self):
        data = export_full_zip([], [], [], "Test")
        assert zipfile.is_zipfile(__import__("io").BytesIO(data))

    def test_zip_partial_data(self):
        """Якщо немає чеків — файл Belege не додається."""
        data = export_full_zip([], [_trip()], [], "Test")
        with zipfile.ZipFile(__import__("io").BytesIO(data)) as zf:
            names = zf.namelist()
        assert not any("Belege" in n for n in names)
        assert any("Fahrten" in n for n in names)
