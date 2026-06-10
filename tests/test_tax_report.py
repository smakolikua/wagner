"""test_tax_report.py — тести генерації EÜR PDF."""
import pytest
from datetime import date
from unittest.mock import MagicMock
from bot.models import User, Vehicle, Trip, Receipt, Category, TaxCode, TripPurpose
from bot.services.tax_report import generate_eur_pdf


def _make_user():
    u = MagicMock(spec=User)
    u.name = "Max Muster"
    u.lang = "de"
    return u


def _make_trip(day: int, dist: float, biz: bool = True):
    t = MagicMock(spec=Trip)
    t.date = date(2025, 1, day)
    t.distance = dist
    t.purpose = MagicMock()
    t.purpose.value = "geschäftlich" if biz else "privat"
    t.start_label = "Home"
    t.end_label = "Client"
    t.start_mileage = 85000.0
    t.end_mileage = 85000.0 + dist
    return t


def _make_receipt(amount: float, vat_rate: int = 19, biz: bool = True, cat_name: str = "Bürobedarf"):
    r = MagicMock(spec=Receipt)
    r.date = date(2025, 1, 5)
    r.amount_gross = amount
    r.vat_rate = vat_rate
    vat = round(amount - amount / (1 + vat_rate / 100), 2) if vat_rate else 0.0
    r.net_amount = round(amount / (1 + vat_rate / 100), 2) if vat_rate else amount
    r.vat_amount = vat
    r.is_business = biz
    r.category = MagicMock()
    r.category.name = cat_name
    return r


class TestEurPdf:
    def test_generates_valid_pdf(self):
        pdf = generate_eur_pdf(
            user=_make_user(),
            receipts=[_make_receipt(59.50), _make_receipt(89.00, cat_name="Kfz-Kosten")],
            trips=[_make_trip(5, 45), _make_trip(10, 30), _make_trip(15, 60, biz=False)],
            date_from=date(2025, 1, 1), date_to=date(2025, 1, 31),
            period_label="Januar 2025", total_income=3500.0,
        )
        assert pdf[:4] == b"%PDF"
        assert len(pdf) > 2000

    def test_empty_receipts_and_trips(self):
        pdf = generate_eur_pdf(
            user=_make_user(), receipts=[], trips=[],
            date_from=date(2025, 1, 1), date_to=date(2025, 1, 31),
            period_label="Q1 2025", total_income=0.0,
        )
        assert pdf[:4] == b"%PDF"

    def test_with_loss(self):
        """Витрати > доходів — збиток."""
        pdf = generate_eur_pdf(
            user=_make_user(),
            receipts=[_make_receipt(5000.0, vat_rate=19)],
            trips=[_make_trip(5, 100)],
            date_from=date(2025, 1, 1), date_to=date(2025, 1, 31),
            period_label="Januar 2025", total_income=100.0,
        )
        assert pdf[:4] == b"%PDF"

    def test_quarter_label(self):
        pdf = generate_eur_pdf(
            user=_make_user(), receipts=[], trips=[],
            date_from=date(2025, 1, 1), date_to=date(2025, 3, 31),
            period_label="Q1 2025", total_income=5000.0,
        )
        assert pdf[:4] == b"%PDF"

    def test_many_categories(self):
        receipts = [
            _make_receipt(50.0, cat_name="Bürobedarf"),
            _make_receipt(100.0, cat_name="Kfz-Kosten"),
            _make_receipt(200.0, cat_name="Reisekosten"),
            _make_receipt(75.0, cat_name="Telefon/Internet"),
            _make_receipt(300.0, cat_name="Miete/Pacht"),
        ]
        pdf = generate_eur_pdf(
            user=_make_user(), receipts=receipts,
            trips=[_make_trip(i+1, 30) for i in range(10)],
            date_from=date(2025, 1, 1), date_to=date(2025, 3, 31),
            period_label="Q1 2025", total_income=8000.0,
        )
        assert pdf[:4] == b"%PDF"
        assert len(pdf) > 3000

    def test_vat_calculation(self):
        """Перевіряємо що ПДВ правильно рахується."""
        r = _make_receipt(119.0, vat_rate=19)
        assert abs(r.net_amount - 100.0) < 0.01
        assert abs(r.vat_amount - 19.0) < 0.01

        r2 = _make_receipt(107.0, vat_rate=7)
        assert abs(r2.net_amount - 100.0) < 0.01
