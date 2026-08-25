"""Pure scheduling calculations for Sourdough Manager."""
from __future__ import annotations

from datetime import UTC, datetime, time, timedelta
from typing import Any
from uuid import NAMESPACE_URL, uuid5

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


def feed_id(feed: dict[str, Any], index: int = 0) -> str:
    """Return a stable ID, deriving one for a legacy feed when necessary."""
    existing = feed.get("id")
    if isinstance(existing, str) and existing:
        return existing
    identity = ":".join(
        (
            str(index),
            str(feed.get("fed_at", "")),
            str(feed.get("location", "")),
            str(feed.get("due_at", "")),
        )
    )
    return uuid5(NAMESPACE_URL, f"sourdough-manager:{identity}").hex


def normalise_feed_history(history: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Add stable IDs to stored feed records without changing their order."""
    return [{**item, "id": feed_id(item, index)} for index, item in enumerate(history)]


def newest_feed(history: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Return the newest valid feed record."""
    valid = [item for item in history if parse_datetime(item.get("fed_at"))]
    if not valid:
        return None
    return max(valid, key=lambda item: parse_datetime(item.get("fed_at")))


def update_feed_record(
    history: list[dict[str, Any]], selected_id: str, fed_at: datetime
) -> list[dict[str, Any]]:
    """Replace one feed timestamp in place and recalculate its timing metadata."""
    updated: list[dict[str, Any]] = []
    found = False
    for item in history:
        if item.get("id") != selected_id:
            updated.append(item)
            continue
        due_at = parse_datetime(item.get("due_at"))
        updated.append(
            {
                **item,
                "fed_at": fed_at.isoformat(),
                "minutes_after_due": minutes_after_due(fed_at, due_at),
            }
        )
        found = True
    if not found:
        raise ValueError("The selected feed no longer exists")
    return updated


def delete_feed_record(
    history: list[dict[str, Any]], selected_id: str
) -> list[dict[str, Any]]:
    """Delete exactly one selected feed record."""
    updated = [item for item in history if item.get("id") != selected_id]
    if len(updated) == len(history):
        raise ValueError("The selected feed no longer exists")
    return updated


def next_feed_due(
    last_fed: datetime | None,
    location: str,
    bench_hours: float,
    fridge_hours: float,
) -> datetime | None:
    """Calculate when the next feeding becomes due."""
    if last_fed is None:
        return None
    interval = fridge_hours if location == LOCATION_FRIDGE else bench_hours
    return last_fed + timedelta(hours=interval)


def align_deadline_to_preferred_time(
    due: datetime | None,
    preferred: str | time,
) -> datetime | None:
    """Align a due time to a preferred clock time in its own timezone."""
    if due is None:
        return None
    clock = parse_clock(preferred)
    return due.replace(
        hour=clock.hour,
        minute=clock.minute,
        second=0,
        microsecond=0,
    )


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


def due_today_or_overdue(
    due: datetime | None,
    now: datetime | None = None,
) -> bool:
    """Return whether a due time is on or before the current local date."""
    if due is None:
        return False
    now = now or datetime.now(due.tzinfo or UTC)
    if due.tzinfo is not None:
        now = now.astimezone(due.tzinfo)
    return due.date() <= now.date()


def overdue_hours(due: datetime | None, now: datetime | None = None) -> float:
    """Return hours overdue, clamped at zero."""
    if due is None:
        return 0.0
    delta = ((now or datetime.now(UTC)) - due).total_seconds() / 3600
    return round(max(0.0, delta), 1)


def minutes_after_due(fed_at: datetime, due: datetime | None) -> int | None:
    """Return neutral elapsed minutes after due, or zero when fed early."""
    if due is None:
        return None
    return max(0, int((fed_at - due).total_seconds() // 60))


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
    """Return neutral copy describing time elapsed since feeding was due."""
    delay = human_duration(hours_overdue)
    if hours_overdue < 2:
        return (
            f"{starter_name} feeding is due",
            f"{starter_name} is now due to be fed.",
        )
    if hours_overdue < 12:
        return (
            f"{starter_name} is waiting for a feed",
            f"{starter_name} has been due for {delay}. Feed it when you can.",
        )
    if hours_overdue < 24:
        return (
            f"{starter_name} is still waiting for a feed",
            f"{starter_name} has been due for {delay}.",
        )
    return (
        f"{starter_name} feeding remains due",
        f"{starter_name} has been due for {delay}. Feed it when convenient.",
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


def light_restore_data(attributes: dict[str, Any]) -> dict[str, Any]:
    """Extract restorable light settings from Home Assistant state attributes."""
    data: dict[str, Any] = {}
    if attributes.get("brightness") is not None:
        data["brightness"] = attributes["brightness"]
    color_mode = attributes.get("color_mode")
    color_keys = {
        "hs": "hs_color",
        "xy": "xy_color",
        "rgb": "rgb_color",
        "rgbw": "rgbw_color",
        "rgbww": "rgbww_color",
        "color_temp": "color_temp_kelvin",
    }
    if (key := color_keys.get(color_mode)) and attributes.get(key) is not None:
        data[key] = attributes[key]
    if attributes.get("effect") is not None:
        data["effect"] = attributes["effect"]
    return data


def migrate_storage(old: dict[str, Any], default_location: str) -> dict[str, Any]:
    """Reduce an older detailed store to the focused schema."""
    last_fed = old.get("last_fed")
    if not last_fed and (cycle := old.get("active_cycle")):
        last_fed = cycle.get("fed_at")
    location = old.get("location", default_location)
    history = normalise_feed_history(list(old.get("feed_history", []))[-20:])
    selected_id = old.get("selected_feed_id")
    if not any(item["id"] == selected_id for item in history):
        latest = newest_feed(history)
        selected_id = latest["id"] if latest else None
    selected = next(
        (item for item in history if item["id"] == selected_id), None
    )
    edit_at = old.get("feed_edit_at")
    if parse_datetime(edit_at) is None:
        edit_at = selected.get("fed_at") if selected else None
    return {
        "schema_version": 8,
        "last_fed": last_fed,
        "location": location,
        "location_changed_at": old.get("location_changed_at"),
        "last_reminder_for": old.get("last_reminder_for"),
        "last_overdue_reminder_at": old.get("last_overdue_reminder_at"),
        "last_reminder_sent_at": old.get("last_reminder_sent_at"),
        "snoozed_until": old.get("snoozed_until"),
        "snooze_hours": old.get("snooze_hours", "1"),
        "last_audio_reminder_at": old.get("last_audio_reminder_at"),
        "last_light_reminder_at": old.get("last_light_reminder_at"),
        "reminders_enabled": old.get("reminders_enabled", True),
        "push_reminders_enabled": old.get("push_reminders_enabled", True),
        "audio_reminders_enabled": old.get("audio_reminders_enabled"),
        "light_reminders_enabled": old.get("light_reminders_enabled", True),
        "silent_until_next_feed": old.get("silent_until_next_feed", False),
        "disruptive_reminder_count": int(
            old.get("disruptive_reminder_count", 0)
        ),
        "deadline_override": old.get("deadline_override"),
        "delay_option": old.get("delay_option", "1"),
        "feed_history": history,
        "selected_feed_id": selected_id,
        "feed_edit_at": edit_at,
        "last_event_type": old.get("last_event_type"),
        "last_event_at": old.get("last_event_at"),
    }
