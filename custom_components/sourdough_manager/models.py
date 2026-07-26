"""Pure scheduling calculations for Sourdough Manager."""
from __future__ import annotations

from datetime import UTC, datetime, time, timedelta
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


def human_duration(hours: float) -> str:
    """Format an hour value as a concise human-friendly duration."""
    total_minutes = round(hours * 60)
    days, remaining_minutes = divmod(total_minutes, 24 * 60)
    whole_hours, minutes = divmod(remaining_minutes, 60)
    parts: list[str] = []
    for value, label in ((days, "day"), (whole_hours, "hour"), (minutes, "minute")):
        if value:
            parts.append(f"{value} {label}{'' if value == 1 else 's'}")
    return " ".join(parts) or "Disabled"


def parse_clock(value: str | time) -> time:
    """Parse a stored Home Assistant time-selector value."""
    if isinstance(value, time):
        return value.replace(tzinfo=None)
    return time.fromisoformat(value)


def quiet_hours_active(
    now: datetime,
    enabled: bool,
    start: str | time,
    end: str | time,
) -> bool:
    """Return whether a local datetime falls inside the quiet period."""
    if not enabled:
        return False
    start_time = parse_clock(start)
    end_time = parse_clock(end)
    current = now.time().replace(tzinfo=None)
    if start_time == end_time:
        return False
    if start_time < end_time:
        return start_time <= current < end_time
    return current >= start_time or current < end_time


def human_clock_range(start: str | time, end: str | time) -> str:
    """Format quiet-hour values without exposing stored seconds."""
    def _format(value: str | time) -> str:
        parsed = parse_clock(value)
        hour = parsed.hour % 12 or 12
        return f"{hour}:{parsed.minute:02d} {'am' if parsed.hour < 12 else 'pm'}"

    return f"{_format(start)} to {_format(end)}"


def overdue_notification_copy(
    starter_name: str, hours_overdue: float
) -> tuple[str, str]:
    """Return progressively firmer overdue notification copy."""
    delay = human_duration(hours_overdue)
    if hours_overdue < 2:
        return (
            f"{starter_name} feeding is due",
            f"{starter_name} is now due to be fed.",
        )
    if hours_overdue < 12:
        return (
            f"{starter_name} feeding is overdue",
            f"{starter_name} is {delay} overdue. Please feed it when you can.",
        )
    if hours_overdue < 24:
        return (
            f"{starter_name} needs feeding",
            f"{starter_name} is {delay} overdue and needs attention soon.",
        )
    return (
        f"{starter_name} is seriously overdue",
        f"{starter_name} is {delay} overdue. Please feed it as soon as possible.",
    )


def audio_reminder_due(
    now: datetime,
    due: datetime,
    lead_hours: float,
    last_sent: datetime | None,
    interval_minutes: float,
) -> bool:
    """Return whether an audio reminder should be spoken now."""
    if now < due - timedelta(hours=lead_hours):
        return False
    return last_sent is None or now - last_sent >= timedelta(
        minutes=interval_minutes
    )


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
        "last_reminder_for": old.get("last_reminder_for"),
        "last_overdue_reminder_at": old.get("last_overdue_reminder_at"),
        "last_reminder_sent_at": old.get("last_reminder_sent_at"),
        "snoozed_until": old.get("snoozed_until"),
        "snooze_hours": old.get("snooze_hours", "1"),
        "last_audio_reminder_at": old.get("last_audio_reminder_at"),
    }
