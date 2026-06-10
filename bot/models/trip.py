import enum
from datetime import date as dt_date
from typing import Optional, TYPE_CHECKING
from sqlalchemy import ForeignKey, String, Float, Date as SADate, Enum, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base, TimestampMixin

if TYPE_CHECKING:
    from .user import User
    from .vehicle import Vehicle
    from .address import Address


class TripPurpose(str, enum.Enum):
    BUSINESS = "geschäftlich"
    PRIVATE = "privat"


class Trip(Base, TimestampMixin):
    __tablename__ = "trips"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    vehicle_id: Mapped[int] = mapped_column(ForeignKey("vehicles.id", ondelete="CASCADE"))

    date: Mapped[dt_date] = mapped_column(SADate)

    start_address_id: Mapped[Optional[int]] = mapped_column(ForeignKey("addresses.id", ondelete="SET NULL"), default=None)
    end_address_id: Mapped[Optional[int]] = mapped_column(ForeignKey("addresses.id", ondelete="SET NULL"), default=None)

    # Для випадків коли адреса не збережена (нова невідома локація)
    start_address_text: Mapped[Optional[str]] = mapped_column(String(255), default=None)
    end_address_text: Mapped[Optional[str]] = mapped_column(String(255), default=None)

    start_mileage: Mapped[float] = mapped_column(Float)
    end_mileage: Mapped[float] = mapped_column(Float)

    purpose: Mapped[TripPurpose] = mapped_column(Enum(TripPurpose), default=TripPurpose.BUSINESS)
    notes: Mapped[Optional[str]] = mapped_column(String(500), default=None)

    is_auto: Mapped[bool] = mapped_column(Boolean, default=False)

    user: Mapped["User"] = relationship(back_populates="trips")
    vehicle: Mapped["Vehicle"] = relationship(back_populates="trips")
    start_address: Mapped[Optional["Address"]] = relationship(foreign_keys=[start_address_id])
    end_address: Mapped[Optional["Address"]] = relationship(foreign_keys=[end_address_id])

    @property
    def distance(self) -> float:
        return round(self.end_mileage - self.start_mileage, 1)

    @property
    def start_label(self) -> str:
        # Використовуємо text-поле як пріоритет якщо address не завантажений
        if self.start_address_text:
            return self.start_address_text
        try:
            if self.start_address:
                return self.start_address.label
        except Exception:
            pass
        return "—"

    @property
    def end_label(self) -> str:
        if self.end_address_text:
            return self.end_address_text
        try:
            if self.end_address:
                return self.end_address.label
        except Exception:
            pass
        return "—"

    def __repr__(self) -> str:
        return f"<Trip id={self.id} date={self.date} km={self.distance} purpose={self.purpose}>"
