from datetime import date, datetime
from typing import Optional


def fmt_date(d: date) -> str:
    return d.strftime("%d.%m.%Y")


def fmt_km(km: float) -> str:
    return f"{km:,.1f}".replace(",", ".")


def fmt_mileage(km: float) -> str:
    return f"{int(km):,}".replace(",", ".")


def fmt_datetime(dt: datetime) -> str:
    return dt.strftime("%d.%m.%Y %H:%M")
