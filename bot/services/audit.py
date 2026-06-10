import json
from datetime import date, datetime
from enum import Enum
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from ..models import AuditLog, User


def _clean_value(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return value


def snapshot(obj: Any, fields: list[str]) -> dict[str, Any]:
    return {field: _clean_value(getattr(obj, field, None)) for field in fields}


def diff(before: dict[str, Any], after: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        key: {"before": before.get(key), "after": after.get(key)}
        for key in sorted(set(before) | set(after))
        if before.get(key) != after.get(key)
    }


async def log_audit(
    session: AsyncSession,
    user: User,
    action: str,
    entity_type: str,
    summary: str,
    *,
    entity_id: Optional[int] = None,
    telegram_id: Optional[int] = None,
    before: Optional[dict[str, Any]] = None,
    after: Optional[dict[str, Any]] = None,
) -> None:
    session.add(
        AuditLog(
            user_id=user.id,
            telegram_id=telegram_id,
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
            summary=summary[:500],
            before_json=json.dumps(before, ensure_ascii=False, sort_keys=True) if before else None,
            after_json=json.dumps(after, ensure_ascii=False, sort_keys=True) if after else None,
        )
    )
