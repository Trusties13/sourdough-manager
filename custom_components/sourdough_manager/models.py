"""Pure scheduling calculations for Sourdough Manager."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

LOCATION_FRIDGE = "refrigerator"


def parse_datetime(value: str | datetime | None) -> datetime | None:
    """Return an aware datetime from a stored value."""
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    else:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed


def next_feed_due(
    last_fed: datetime | None,
    location: str,
    bench_hours: float,
    fridge_hours: float,
) -> datetime | None:
    """Calculate the next feeding deadline."""
    if last_fed is None:
        return None
    interval = fridge_hours if location == LOCATION_FRIDGE else bench_hours
    return last_fed + timedelta(hours=interval)


def schedule_state(
    due: datetime | None,
    due_soon_hours: float,
    now: datetime | None = None,
) -> tuple[bool, bool]:
    """Return due and due-soon states."""
    if due is None:
        return False, False
    now = now or datetime.now(UTC)
    is_due = now >= due
    is_due_soon = not is_due and now >= due - timedelta(hours=due_soon_hours)
    return is_due, is_due_soon


def overdue_hours(due: datetime | None, now: datetime | None = None) -> float:
    """Return hours overdue, clamped at zero."""
    if due is None:
        return 0.0
    delta = ((now or datetime.now(UTC)) - due).total_seconds() / 3600
    return round(max(0.0, delta), 1)


def migrate_storage(old: dict[str, Any], default_location: str) -> dict[str, Any]:
    """Reduce an older detailed store to the focused schema."""
    last_fed = old.get("last_fed")
    if not last_fed and (cycle := old.get("active_cycle")):
        last_fed = cycle.get("fed_at")
    location = old.get("location", default_location)
    return {
        "schema_version": 3,
        "last_fed": last_fed,
        "location": location,
        "location_changed_at": old.get("location_changed_at"),
    }
