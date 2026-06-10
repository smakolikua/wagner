from typing import Optional, List, TYPE_CHECKING
from sqlalchemy import ForeignKey, String, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base, TimestampMixin

if TYPE_CHECKING:
    from .user import User
    from .trip import Trip


class Vehicle(Base, TimestampMixin):
    __tablename__ = "vehicles"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    make: Mapped[str] = mapped_column(String(50))
    model: Mapped[str] = mapped_column(String(50))
    plate: Mapped[str] = mapped_column(String(20))
    current_mileage: Mapped[float] = mapped_column(Float, default=0.0)
    is_active: Mapped[bool] = mapped_column(default=True)

    user: Mapped["User"] = relationship(back_populates="vehicles")
    trips: Mapped[List["Trip"]] = relationship(back_populates="vehicle")

    @property
    def display_name(self) -> str:
        return f"{self.make} {self.model} ({self.plate})"

    def __repr__(self) -> str:
        return f"<Vehicle id={self.id} plate={self.plate} mileage={self.current_mileage}>"
