import enum
from typing import Optional
from sqlalchemy import ForeignKey, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base, TimestampMixin


class TaxPeriodStatus(str, enum.Enum):
    DRAFT     = "draft"      # в роботі
    READY     = "ready"      # готово до подачі
    SUBMITTED = "submitted"  # подано до Finanzamt


class TaxPeriod(Base, TimestampMixin):
    __tablename__ = "tax_periods"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )

    year: Mapped[int] = mapped_column(Integer)
    quarter: Mapped[Optional[int]] = mapped_column(Integer, default=None)  # 1-4, None = весь рік

    # Підсумки (обчислюються при генерації звіту)
    total_income: Mapped[float] = mapped_column(Float, default=0.0)
    total_expenses: Mapped[float] = mapped_column(Float, default=0.0)
    vat_collected: Mapped[float] = mapped_column(Float, default=0.0)   # USt eingenommen
    vat_paid: Mapped[float] = mapped_column(Float, default=0.0)        # VSt bezahlt
    vat_to_pay: Mapped[float] = mapped_column(Float, default=0.0)      # Zahllast

    status: Mapped[TaxPeriodStatus] = mapped_column(default=TaxPeriodStatus.DRAFT)
    notes: Mapped[Optional[str]] = mapped_column(String(500), default=None)

    @property
    def profit(self) -> float:
        return round(self.total_income - self.total_expenses, 2)

    @property
    def label(self) -> str:
        if self.quarter:
            return f"Q{self.quarter} {self.year}"
        return str(self.year)

    def __repr__(self) -> str:
        return f"<TaxPeriod id={self.id} {self.label} status={self.status}>"
