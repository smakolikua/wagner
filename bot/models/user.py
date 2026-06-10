from typing import Optional, List, TYPE_CHECKING
from sqlalchemy import BigInteger, String, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base, TimestampMixin

if TYPE_CHECKING:
    from .user_account import UserAccount
    from .vehicle import Vehicle
    from .address import Address
    from .trip import Trip


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    name: Mapped[str] = mapped_column(String(100))
    lang: Mapped[str] = mapped_column(String(5), default="de")
    access_pin_hash: Mapped[Optional[str]] = mapped_column(String(64), unique=True, index=True, default=None)
    home_address_id: Mapped[Optional[int]] = mapped_column(default=None)
    geofence_radius: Mapped[int] = mapped_column(Integer, default=100)

    accounts: Mapped[List["UserAccount"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    vehicles: Mapped[List["Vehicle"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    addresses: Mapped[List["Address"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    trips: Mapped[List["Trip"]] = relationship(back_populates="user", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<User id={self.id} telegram_id={self.telegram_id} name={self.name}>"
