from datetime import date as dt_date
from decimal import Decimal
from typing import Optional, List, TYPE_CHECKING
from sqlalchemy import ForeignKey, String, Float, Date as SADate, Boolean, Text, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base, TimestampMixin

if TYPE_CHECKING:
    from .user import User
    from .category import Category
    from .trip import Trip


class VatRate(int):
    """Ставки ПДВ в Германії."""
    NONE     = 0
    REDUCED  = 7
    STANDARD = 19


class Receipt(Base, TimestampMixin):
    __tablename__ = "receipts"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    category_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("categories.id", ondelete="SET NULL"), default=None
    )
    trip_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("trips.id", ondelete="SET NULL"), default=None,
        index=True,
    )  # якщо витрата пов'язана з конкретною поїздкою

    # Дані з чека
    date: Mapped[dt_date] = mapped_column(SADate)
    amount_gross: Mapped[float] = mapped_column(Float)         # сума з ПДВ
    amount_net: Mapped[Optional[float]] = mapped_column(Float, default=None)   # без ПДВ
    vat_amount: Mapped[Optional[float]] = mapped_column(Float, default=None)   # сума ПДВ
    vat_rate: Mapped[int] = mapped_column(Integer, default=0)  # 0/7/19

    vendor: Mapped[Optional[str]] = mapped_column(String(200), default=None)
    description: Mapped[Optional[str]] = mapped_column(String(500), default=None)

    # Telegram photo
    photo_file_id: Mapped[Optional[str]] = mapped_column(String(255), default=None)

    # OCR результат
    raw_ocr_text: Mapped[Optional[str]] = mapped_column(Text, default=None)
    ai_confidence: Mapped[Optional[float]] = mapped_column(Float, default=None)  # 0.0–1.0

    is_business: Mapped[bool] = mapped_column(Boolean, default=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)  # підтверджено юзером

    user: Mapped["User"] = relationship(foreign_keys=[user_id])
    category: Mapped[Optional["Category"]] = relationship(back_populates="receipts")
    trip: Mapped[Optional["Trip"]] = relationship(foreign_keys=[trip_id])

    @property
    def amount_display(self) -> str:
        return f"{self.amount_gross:.2f} €"

    @property
    def net_amount(self) -> float:
        """Сума без ПДВ для EÜR."""
        if self.amount_net is not None:
            return self.amount_net
        if self.vat_rate and self.vat_rate > 0:
            return round(self.amount_gross / (1 + self.vat_rate / 100), 2)
        return self.amount_gross

    def __repr__(self) -> str:
        return f"<Receipt id={self.id} date={self.date} amount={self.amount_gross}€>"
