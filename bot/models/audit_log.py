from datetime import datetime
from typing import Optional, TYPE_CHECKING

from sqlalchemy import BigInteger, DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .user import User


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    telegram_id: Mapped[Optional[int]] = mapped_column(BigInteger, index=True, default=None)
    entity_type: Mapped[str] = mapped_column(String(50), index=True)
    entity_id: Mapped[Optional[int]] = mapped_column(index=True, default=None)
    action: Mapped[str] = mapped_column(String(30), index=True)
    summary: Mapped[str] = mapped_column(String(500))
    before_json: Mapped[Optional[str]] = mapped_column(Text, default=None)
    after_json: Mapped[Optional[str]] = mapped_column(Text, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), index=True)

    user: Mapped["User"] = relationship()
