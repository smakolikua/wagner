import enum
from typing import Optional, TYPE_CHECKING
from sqlalchemy import ForeignKey, String, Float, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base, TimestampMixin

if TYPE_CHECKING:
    from .user import User


class AddressType(str, enum.Enum):
    HOME = "Heimatadresse"
    CLIENT = "Kunde"
    OFFICE = "Büro"
    OTHER = "Sonstiges"


class Address(Base, TimestampMixin):
    __tablename__ = "addresses"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    label: Mapped[str] = mapped_column(String(100))
    address_str: Mapped[str] = mapped_column(String(255))
    lat: Mapped[Optional[float]] = mapped_column(Float, default=None)
    lon: Mapped[Optional[float]] = mapped_column(Float, default=None)
    type: Mapped[AddressType] = mapped_column(Enum(AddressType), default=AddressType.OTHER)

    user: Mapped["User"] = relationship(back_populates="addresses")

    @property
    def has_coords(self) -> bool:
        return self.lat is not None and self.lon is not None

    @property
    def coords(self) -> Optional[tuple]:
        if self.has_coords:
            return (self.lat, self.lon)
        return None

    def __repr__(self) -> str:
        return f"<Address id={self.id} label={self.label} type={self.type}>"
