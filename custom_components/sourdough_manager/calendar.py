"""Feeding schedule calendar."""
from __future__ import annotations

from datetime import timedelta

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.util import dt as dt_util

from .entity import StarterEntity
from .models import parse_datetime


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up the feeding calendar."""
    async_add_entities([FeedingCalendar(entry.runtime_data)])


class FeedingCalendar(StarterEntity, CalendarEntity):
    """Expose completed feeds and the next due time as calendar events."""

    _attr_translation_key = "feeding_calendar"

    def __init__(self, coordinator):
        super().__init__(coordinator, "feeding_calendar")

    @property
    def event(self) -> CalendarEvent | None:
        """Return the current or next feeding due time."""
        due = self.coordinator.next_due()
        if due is None:
            return None
        return CalendarEvent(
            start=due,
            end=due + timedelta(minutes=30),
            summary=f"Feed {self.coordinator.entry.title}",
            description="Scheduled by Sourdough Manager",
        )

    async def async_get_events(self, hass, start_date, end_date):
        """Return feed-history events and the next due time in a time range."""
        events: list[CalendarEvent] = []
        for item in self.coordinator.data.get("feed_history", []):
            fed_at = parse_datetime(item.get("fed_at"))
            if fed_at is None or not start_date <= fed_at < end_date:
                continue
            timing = item.get("minutes_after_due")
            description = f"Storage: {item.get('location', 'unknown')}"
            if isinstance(timing, int) and timing > 0:
                description += f"; fed {timing} minutes after due time"
            events.append(
                CalendarEvent(
                    start=fed_at,
                    end=fed_at + timedelta(minutes=15),
                    summary=f"{self.coordinator.entry.title} fed",
                    description=description,
                )
            )
        due = self.coordinator.next_due()
        if due is not None and start_date <= due < end_date:
            events.append(
                CalendarEvent(
                    start=due,
                    end=due + timedelta(minutes=30),
                    summary=f"Feed {self.coordinator.entry.title}",
                    description=(
                        f"Due {dt_util.as_local(due).strftime('%-I:%M %p')}"
                    ),
                )
            )
        return sorted(events, key=lambda item: item.start)
