"""Income — таблиця доходів (Einnahmen)."""
from datetime import date as dt_date
from typing import Optional, TYPE_CHECKING
from sqlalchemy import ForeignKey, String, Float, Date as SADate, Integer, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base, TimestampMixin

if TYPE_CHECKING:
    from .user import User


class Income(Base, TimestampMixin):
    __tablename__ = "incomes"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )

    date: Mapped[dt_date] = mapped_column(SADate)
    amount: Mapped[float] = mapped_column(Float)               # сума без ПДВ
    vat_amount: Mapped[float] = mapped_column(Float, default=0.0)   # ПДВ отриманий
    vat_rate: Mapped[int] = mapped_column(Integer, default=0)  # 0 / 7 / 19

    description: Mapped[Optional[str]] = mapped_column(String(500), default=None)
    invoice_number: Mapped[Optional[str]] = mapped_column(String(100), default=None)
    client_name: Mapped[Optional[str]] = mapped_column(String(200), default=None)
    is_kleinunternehmer: Mapped[bool] = mapped_column(Boolean, default=False)

    user: Mapped["User"] = relationship(foreign_keys=[user_id])

    @property
    def gross_amount(self) -> float:
        return round(self.amount + self.vat_amount, 2)

    @property
    def display(self) -> str:
        return f"{self.amount:.2f} €" + (f" + {self.vat_amount:.2f} € MwSt" if self.vat_amount else "")

    def __repr__(self) -> str:
        return f"<Income id={self.id} date={self.date} amount={self.amount}€>"
