"""
geo.py — геокодинг, геофенсинг і логіка накопичення треку.

Фаза 2:
- Кешування геокодингу (уникаємо rate-limit Nominatim)
- Клас TrackAccumulator — накопичення точок між зупинками
- Dwell detection — визначення «стоянки» (>60 сек в радіусі 30м)
- Smooth distance — підсумовування відрізків треку замість прямої лінії
"""

import math
import time
from dataclasses import dataclass, field
from typing import Optional, Tuple, List, Dict
from geopy.geocoders import Nominatim
from geopy.adapters import AioHTTPAdapter
from loguru import logger

from ..models import Address

NOMINATIM_UA = "fahrtenbuch-bot/2.0"

_geocode_cache: Dict[str, Optional[Tuple[float, float]]] = {}
_reverse_cache: Dict[Tuple[float, float], str] = {}


async def geocode_address(address_str: str) -> Optional[Tuple[float, float]]:
    key = address_str.strip().lower()
    if key in _geocode_cache:
        return _geocode_cache[key]
    try:
        async with Nominatim(user_agent=NOMINATIM_UA, adapter_factory=AioHTTPAdapter) as g:
            loc = await g.geocode(address_str, language="de")
            if loc:
                result = (loc.latitude, loc.longitude)
                _geocode_cache[key] = result
                return result
    except Exception as e:
        logger.warning(f"Geocoding failed for '{address_str}': {e}")
    _geocode_cache[key] = None
    return None


async def reverse_geocode(lat: float, lon: float) -> Optional[str]:
    cache_key = (round(lat, 3), round(lon, 3))
    if cache_key in _reverse_cache:
        return _reverse_cache[cache_key]
    try:
        async with Nominatim(user_agent=NOMINATIM_UA, adapter_factory=AioHTTPAdapter) as g:
            loc = await g.reverse((lat, lon), language="de")
            if loc:
                _reverse_cache[cache_key] = loc.address
                return loc.address
    except Exception as e:
        logger.warning(f"Reverse geocoding failed for ({lat}, {lon}): {e}")
    return None


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6_371_000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    return round(haversine_distance(lat1, lon1, lat2, lon2) / 1000, 2)


def find_nearest_address(
    lat: float, lon: float, addresses: List[Address], radius_meters: int = 100
) -> Optional[Address]:
    best: Optional[Address] = None
    best_dist = float("inf")
    for addr in addresses:
        if not addr.has_coords:
            continue
        dist = haversine_distance(lat, lon, addr.lat, addr.lon)
        if dist <= radius_meters and dist < best_dist:
            best_dist = dist
            best = addr
    return best


@dataclass
class GpsPoint:
    lat: float
    lon: float
    ts: float = field(default_factory=time.time)


@dataclass
class DwellEvent:
    lat: float
    lon: float
    arrived_at: float
    left_at: Optional[float] = None
    address: Optional[Address] = None
    address_text: Optional[str] = None

    @property
    def duration_sec(self) -> float:
        return (self.left_at or time.time()) - self.arrived_at


class TrackAccumulator:
    DWELL_RADIUS = 30
    DWELL_TIME   = 60
    MIN_MOVE     = 5

    def __init__(self):
        self.points: List[GpsPoint] = []
        self.dwells: List[DwellEvent] = []
        self._dwell_candidate: Optional[DwellEvent] = None
        self._accumulated_km: float = 0.0
        self._in_dwell: bool = False

    def add_point(self, lat: float, lon: float) -> Optional[DwellEvent]:
        now = time.time()
        new_pt = GpsPoint(lat=lat, lon=lon, ts=now)

        if self.points:
            last = self.points[-1]
            moved = haversine_distance(last.lat, last.lon, lat, lon)
            if moved < self.MIN_MOVE:
                self._update_dwell_candidate(lat, lon, now)
                return self._check_dwell_confirmed()

        self.points.append(new_pt)

        if not self._in_dwell and len(self.points) >= 2:
            prev = self.points[-2]
            seg_m = haversine_distance(prev.lat, prev.lon, lat, lon)
            self._accumulated_km += seg_m / 1000

        self._update_dwell_candidate(lat, lon, now)
        return self._check_dwell_confirmed()

    def _update_dwell_candidate(self, lat: float, lon: float, now: float):
        if self._dwell_candidate is None:
            self._dwell_candidate = DwellEvent(lat=lat, lon=lon, arrived_at=now)
        else:
            dist = haversine_distance(
                self._dwell_candidate.lat, self._dwell_candidate.lon, lat, lon
            )
            if dist > self.DWELL_RADIUS:
                if self._in_dwell and self.dwells:
                    self.dwells[-1].left_at = now
                self._in_dwell = False
                self._dwell_candidate = DwellEvent(lat=lat, lon=lon, arrived_at=now)

    def _check_dwell_confirmed(self) -> Optional[DwellEvent]:
        if self._dwell_candidate and not self._in_dwell:
            if time.time() - self._dwell_candidate.arrived_at >= self.DWELL_TIME:
                self._in_dwell = True
                self.dwells.append(self._dwell_candidate)
                return self._dwell_candidate
        return None

    def flush_km(self) -> float:
        km = round(self._accumulated_km, 2)
        self._accumulated_km = 0.0
        return km

    @property
    def total_km(self) -> float:
        return round(self._accumulated_km, 2)

    @property
    def point_count(self) -> int:
        return len(self.points)

    def last_point(self) -> Optional[GpsPoint]:
        return self.points[-1] if self.points else None
