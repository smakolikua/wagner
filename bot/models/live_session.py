from datetime import datetime
from typing import Optional
from sqlalchemy import ForeignKey, Float, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base


class LiveSession(Base):
    __tablename__ = "live_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    vehicle_id: Mapped[int] = mapped_column(ForeignKey("vehicles.id", ondelete="CASCADE"))

    started_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime, default=None)

    # Остання відома позиція
    last_lat: Mapped[Optional[float]] = mapped_column(Float, default=None)
    last_lon: Mapped[Optional[float]] = mapped_column(Float, default=None)
    last_update: Mapped[Optional[datetime]] = mapped_column(DateTime, default=None)

    # Пробіг на початок сесії (для підрахунку)
    start_mileage: Mapped[float] = mapped_column(Float, default=0.0)

    # Остання зафіксована адреса (щоб не дублювати записи)
    last_address_id: Mapped[Optional[int]] = mapped_column(ForeignKey("addresses.id", ondelete="SET NULL"), default=None)

    @property
    def is_active(self) -> bool:
        return self.ended_at is None

    def __repr__(self) -> str:
        return f"<LiveSession id={self.id} user_id={self.user_id} active={self.is_active}>"
