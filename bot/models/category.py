import enum
from typing import Optional, List, TYPE_CHECKING
from sqlalchemy import ForeignKey, String, Boolean, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base, TimestampMixin

if TYPE_CHECKING:
    from .receipt import Receipt


class TaxCode(str, enum.Enum):
    """§ 4 EStG / EÜR категорії витрат."""
    BUERO        = "Bürobedarf"           # канцтовари, папір
    KFZ          = "Kfz-Kosten"           # авто: пальне, ремонт, страховка
    REISE        = "Reisekosten"          # відрядження, готелі
    BEWIRTUNG    = "Bewirtungskosten"     # представницькі витрати (70%)
    TELEFON      = "Telefon/Internet"    # зв'язок
    MIETE        = "Miete/Pacht"         # оренда офісу
    ABSCHREIBUNG = "Abschreibungen"      # амортизація
    PERSONAL     = "Personalkosten"      # зарплати
    VERSICHERUNG = "Versicherungen"      # страховки
    MARKETING    = "Werbung/Marketing"   # реклама
    SONSTIGES    = "Sonstige BA"         # інші ділові витрати
    PRIVAT       = "Privat"              # приватні (не ділові)


class Category(Base, TimestampMixin):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, default=None
    )  # None = системна категорія для всіх

    name: Mapped[str] = mapped_column(String(100))
    tax_code: Mapped[TaxCode] = mapped_column(default=TaxCode.SONSTIGES)
    description: Mapped[Optional[str]] = mapped_column(String(255), default=None)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    receipts: Mapped[List["Receipt"]] = relationship(back_populates="category")

    def __repr__(self) -> str:
        return f"<Category id={self.id} name={self.name} tax={self.tax_code}>"


# Вбудовані категорії — вставляються при першому запуску
DEFAULT_CATEGORIES = [
    {"name": "Bürobedarf",        "tax_code": TaxCode.BUERO,        "sort_order": 1},
    {"name": "Kfz-Kosten",        "tax_code": TaxCode.KFZ,          "sort_order": 2},
    {"name": "Reisekosten",       "tax_code": TaxCode.REISE,        "sort_order": 3},
    {"name": "Bewirtung",         "tax_code": TaxCode.BEWIRTUNG,    "sort_order": 4},
    {"name": "Telefon/Internet",  "tax_code": TaxCode.TELEFON,      "sort_order": 5},
    {"name": "Miete/Pacht",       "tax_code": TaxCode.MIETE,        "sort_order": 6},
    {"name": "Abschreibungen",    "tax_code": TaxCode.ABSCHREIBUNG, "sort_order": 7},
    {"name": "Personalkosten",    "tax_code": TaxCode.PERSONAL,     "sort_order": 8},
    {"name": "Versicherungen",    "tax_code": TaxCode.VERSICHERUNG, "sort_order": 9},
    {"name": "Werbung/Marketing", "tax_code": TaxCode.MARKETING,    "sort_order": 10},
    {"name": "Sonstige BA",       "tax_code": TaxCode.SONSTIGES,    "sort_order": 11},
    {"name": "Privat",            "tax_code": TaxCode.PRIVAT,       "sort_order": 99},
]
