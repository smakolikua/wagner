"""
track_store.py — in-memory сховище активних TrackAccumulator-ів.

Кожен користувач має максимум 1 активний акумулятор.
При перезапуску бота сесія втрачається (прийнятно для MVP).
"""

from __future__ import annotations

from typing import Dict
from .geo import TrackAccumulator

_store: Dict[int, TrackAccumulator] = {}


def get_or_create(user_id: int) -> TrackAccumulator:
    if user_id not in _store:
        _store[user_id] = TrackAccumulator()
    return _store[user_id]


def get(user_id: int) -> TrackAccumulator | None:
    return _store.get(user_id)


def remove(user_id: int) -> None:
    _store.pop(user_id, None)


def has_active(user_id: int) -> bool:
    return user_id in _store
