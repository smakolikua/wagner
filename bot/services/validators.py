"""
validators.py — валідатори даних перед збереженням і генерацією звітів.
"""
from dataclasses import dataclass
from typing import Optional
from datetime import date
from ..models import Trip, TripPurpose


@dataclass
class ValidationResult:
    ok: bool
    error: Optional[str] = None


def validate_mileage(start: float, end: float) -> ValidationResult:
    if end < start:
        return ValidationResult(False,
            f"Кінцевий пробіг ({int(end):,} км) менший за початковий ({int(start):,} км)")
    if end - start > 2000:
        return ValidationResult(False,
            f"Відстань {end-start:.0f} км виглядає нереальною. Перевірте дані.")
    if start < 0 or end < 0:
        return ValidationResult(False, "Пробіг не може бути від'ємним.")
    return ValidationResult(True)


def validate_trips_for_pdf(trips: list[Trip]) -> ValidationResult:
    if not trips:
        return ValidationResult(False, "За вказаний період поїздок не знайдено.")
    bad = [t for t in trips if t.end_mileage < t.start_mileage]
    if bad:
        ids = ", ".join(f"#{t.id}" for t in bad[:3])
        return ValidationResult(False,
            f"Поїздки {ids} мають некоректний пробіг (кінець < початок). "
            f"Виправте через /trips перед генерацією звіту.")
    return ValidationResult(True)


def validate_date(d: date) -> ValidationResult:
    today = date.today()
    if d > today:
        return ValidationResult(False, "Дата поїздки не може бути в майбутньому.")
    if (today - d).days > 365 * 5:
        return ValidationResult(False, "Дата занадто давня (більше 5 років).")
    return ValidationResult(True)
