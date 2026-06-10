"""test_geo.py — тести geo сервісу."""
import time
import pytest
from bot.services.geo import (
    haversine_distance, haversine_km,
    find_nearest_address, TrackAccumulator,
)
from bot.models import Address, AddressType
from unittest.mock import MagicMock


def make_addr(lat, lon, label, addr_id=1):
    a = MagicMock(spec=Address)
    a.id = addr_id
    a.lat = lat
    a.lon = lon
    a.label = label
    a.has_coords = True
    return a


class TestHaversine:
    def test_same_point(self):
        assert haversine_distance(48.1351, 11.5820, 48.1351, 11.5820) == 0.0

    def test_munich_points(self):
        # Відстань між двома точками в Мюнхені ~800м
        d = haversine_distance(48.1351, 11.5820, 48.1400, 11.5900)
        assert 750 < d < 900

    def test_km_conversion(self):
        km = haversine_km(48.1351, 11.5820, 48.2351, 11.5820)
        assert 10 < km < 12  # ~11 км


class TestFindNearest:
    def test_finds_in_radius(self):
        addrs = [make_addr(48.1351, 11.5820, "Home")]
        found = find_nearest_address(48.1352, 11.5821, addrs, radius_meters=50)
        assert found is not None
        assert found.label == "Home"

    def test_none_outside_radius(self):
        addrs = [make_addr(48.1351, 11.5820, "Home")]
        found = find_nearest_address(48.2000, 11.6000, addrs, radius_meters=100)
        assert found is None

    def test_picks_nearest_of_two(self):
        addrs = [
            make_addr(48.1351, 11.5820, "Near",  1),
            make_addr(48.1360, 11.5830, "Far",   2),
        ]
        found = find_nearest_address(48.1352, 11.5821, addrs, radius_meters=200)
        assert found.label == "Near"

    def test_skips_no_coords(self):
        a = MagicMock(spec=Address)
        a.has_coords = False
        found = find_nearest_address(48.1352, 11.5821, [a], radius_meters=100)
        assert found is None


class TestTrackAccumulator:
    def test_accumulates_distance(self):
        acc = TrackAccumulator()
        acc.DWELL_TIME = 999  # блокуємо dwell
        acc.MIN_MOVE = 0
        route = [(48.135 + i * 0.001, 11.582) for i in range(6)]
        for lat, lon in route:
            acc.add_point(lat, lon)
        assert acc.total_km > 0.3

    def test_flush_resets(self):
        acc = TrackAccumulator()
        acc.DWELL_TIME = 999
        acc.MIN_MOVE = 0
        for i in range(5):
            acc.add_point(48.135 + i * 0.001, 11.582)
        km = acc.flush_km()
        assert km > 0
        assert acc.total_km == 0.0

    def test_dwell_detection(self):
        acc = TrackAccumulator()
        acc.DWELL_TIME = 1   # 1 секунда
        acc.MIN_MOVE = 0
        acc.add_point(48.1351, 11.5820)
        acc.add_point(48.1351, 11.5821)
        time.sleep(1.1)
        dwell = acc.add_point(48.1351, 11.5822)
        assert dwell is not None

    def test_no_dwell_when_moving(self):
        acc = TrackAccumulator()
        acc.DWELL_TIME = 999
        # Рухаємося — кожна точка далеко від попередньої
        for i in range(5):
            acc.add_point(48.135 + i * 0.01, 11.582)
        assert not acc._in_dwell

    def test_min_move_filter(self):
        acc = TrackAccumulator()
        acc.DWELL_TIME = 999
        acc.MIN_MOVE = 100  # 100 метрів
        # Точки дуже близько — мають фільтруватись
        acc.add_point(48.1351, 11.5820)
        acc.add_point(48.1351, 11.5821)  # < 100м — skip
        assert acc.point_count == 1
