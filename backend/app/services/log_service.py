from datetime import datetime, timezone
import logging
from typing import Any

from sqlalchemy.orm import Session

from app.models import SystemLog


logger = logging.getLogger(__name__)


def record_log(
    db: Session,
    level: str,
    category: str,
    message: str,
    *,
    branch_id: int | None = None,
    source: str | None = None,
    details: dict[str, Any] | None = None,
) -> SystemLog | None:
    try:
        row = SystemLog(
            branch_id=branch_id,
            level=level,
            category=category,
            source=source,
            message=message,
            details=_safe_details(details),
            status="open",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        db.add(row)
        db.flush()
        return row
    except Exception:
        logger.exception("Failed to write system log entry")
        return None


def _safe_details(details: dict[str, Any] | None) -> dict[str, Any] | None:
    if details is None:
        return None
    safe: dict[str, Any] = {}
    for key, value in details.items():
        if isinstance(value, (str, int, float, bool)) or value is None:
            safe[key] = value
        else:
            safe[key] = str(value)
    return safe
