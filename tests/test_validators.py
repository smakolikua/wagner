"""test_validators.py — тести валідаторів."""
import pytest
from datetime import date, timedelta
from unittest.mock import MagicMock
from bot.services.validators import validate_mileage, validate_date, validate_trips_for_pdf
from bot.models import Trip, TripPurpose


class TestMileageValidator:
    def test_valid(self):
        assert validate_mileage(85000, 85045).ok

    def test_end_less_than_start(self):
        v = validate_mileage(85045, 85000)
        assert not v.ok
        assert "85045" in v.error or "менш" in v.error.lower() or "kleiner" in v.error.lower()

    def test_equal_allowed(self):
        assert validate_mileage(85000, 85000).ok

    def test_unrealistic_distance(self):
        v = validate_mileage(1000, 4000)
        assert not v.ok

    def test_negative_not_allowed(self):
        v = validate_mileage(-100, 0)
        assert not v.ok


class TestDateValidator:
    def test_today_ok(self):
        assert validate_date(date.today()).ok

    def test_yesterday_ok(self):
        assert validate_date(date.today() - timedelta(days=1)).ok

    def test_future_not_allowed(self):
        v = validate_date(date.today() + timedelta(days=1))
        assert not v.ok

    def test_too_old_not_allowed(self):
        v = validate_date(date(2000, 1, 1))
        assert not v.ok

    def test_5_years_ago_boundary(self):
        borderline = date.today().replace(year=date.today().year - 4)
        assert validate_date(borderline).ok


class TestPdfValidator:
    def _trip(self, start, end):
        t = MagicMock(spec=Trip)
        t.id = 1
        t.start_mileage = start
        t.end_mileage = end
        t.distance = end - start
        return t

    def test_empty_trips(self):
        v = validate_trips_for_pdf([])
        assert not v.ok

    def test_valid_trips(self):
        trips = [self._trip(85000, 85045), self._trip(85045, 85090)]
        assert validate_trips_for_pdf(trips).ok

    def test_invalid_mileage_in_trip(self):
        trips = [self._trip(85000, 85045), self._trip(85090, 85045)]  # другий поганий
        v = validate_trips_for_pdf(trips)
        assert not v.ok
        assert "1" in v.error  # id поїздки згадується
