from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, ForeignKey
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin

if TYPE_CHECKING:
    from .user import User


class UserAccount(Base, TimestampMixin):
    __tablename__ = "user_accounts"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    role: Mapped[str] = mapped_column(String(20), default="driver")

    user: Mapped["User"] = relationship(back_populates="accounts")

    def __repr__(self) -> str:
        return f"<UserAccount id={self.id} user_id={self.user_id} telegram_id={self.telegram_id}>"
