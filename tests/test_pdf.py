"""test_pdf.py — тести генерації PDF."""
import pytest
from datetime import date
from bot.models import User, Vehicle, Trip, TripPurpose
from bot.services.pdf_report import generate_fahrtenbuch_pdf
from unittest.mock import MagicMock


def _make_user():
    u = MagicMock(spec=User)
    u.name = "Max Mustermann"
    u.lang = "de"
    return u


def _make_vehicle():
    v = MagicMock(spec=Vehicle)
    v.display_name = "VW Golf (M-AB 1234)"
    v.current_mileage = 85000.0
    return v


def _make_trips(count: int = 3):
    from datetime import timedelta
    trips = []
    km = 85000.0
    base = date(2025, 1, 1)
    for i in range(count):
        t = MagicMock(spec=Trip)
        t.date = base + timedelta(days=i)
        t.start_label = "Heimat"
        t.end_label = f"Kunde {i+1}"
        t.start_mileage = km
        t.end_mileage = km + 45
        t.distance = 45.0
        t.purpose = TripPurpose.BUSINESS if i % 2 == 0 else TripPurpose.PRIVATE
        t.notes = f"Note {i}" if i % 3 == 0 else None
        trips.append(t)
        km += 45
    return trips


class TestPdfGeneration:
    def test_generates_valid_pdf(self):
        pdf = generate_fahrtenbuch_pdf(
            _make_user(), _make_vehicle(), _make_trips(5),
            "Januar 2025", date(2025, 1, 1), date(2025, 1, 31),
        )
        assert pdf[:4] == b"%PDF"
        assert len(pdf) > 1000

    def test_single_trip(self):
        pdf = generate_fahrtenbuch_pdf(
            _make_user(), _make_vehicle(), _make_trips(1),
            "Test", date(2025, 1, 1), date(2025, 1, 31),
        )
        assert pdf[:4] == b"%PDF"

    def test_many_trips(self):
        pdf = generate_fahrtenbuch_pdf(
            _make_user(), _make_vehicle(), _make_trips(50),
            "Q1 2025", date(2025, 1, 1), date(2025, 3, 31),
        )
        assert pdf[:4] == b"%PDF"
        assert len(pdf) > 5000

    def test_business_vs_private_counted(self):
        trips = _make_trips(4)
        # trips 0,2 — business; 1,3 — private (за логікою _make_trips)
        biz  = sum(t.distance for t in trips if t.purpose == TripPurpose.BUSINESS)
        priv = sum(t.distance for t in trips if t.purpose == TripPurpose.PRIVATE)
        assert biz == 90.0   # 2 поїздки × 45
        assert priv == 90.0
