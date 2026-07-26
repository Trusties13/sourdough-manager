"""Runtime coordinator."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from .const import (
    CONF_BENCH_INTERVAL,
    CONF_DUE_SOON,
    CONF_FRIDGE_INTERVAL,
    CONF_LAST_FED,
    CONF_LOCATION,
    CONF_NOTIFICATION_TARGETS,
    DEFAULT_BENCH_INTERVAL,
    DEFAULT_DUE_SOON,
    DEFAULT_FRIDGE_INTERVAL,
    DOMAIN,
    EVENT_DUE_SOON,
    EVENT_FEED_RECORDED,
    EVENT_LOCATION_CHANGED,
    EVENT_OVERDUE,
    LOCATION_BENCH,
)
from .models import next_feed_due, parse_datetime, schedule_state
from .storage import StarterStore


class SourdoughCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Own scheduling state and mutations for one starter."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(
            hass,
            logger=__import__("logging").getLogger(__name__),
            name=f"{DOMAIN}_{entry.entry_id}",
            update_interval=timedelta(minutes=1),
        )
        self.entry = entry
        self.store = StarterStore(hass, entry.entry_id)
        self._was_due = False
        self._was_due_soon = False

    def option(self, key: str, default: Any) -> Any:
        """Return an option, falling back to config data."""
        return self.entry.options.get(key, self.entry.data.get(key, default))

    async def async_load(self) -> None:
        """Load persisted data and initialise threshold state."""
        data = await self.store.load(
            self.entry.data.get(CONF_LOCATION, LOCATION_BENCH),
            self.entry.data.get(CONF_LAST_FED),
        )
        self.async_set_updated_data(data)
        self._was_due = False
        self._was_due_soon = False

    def next_due(self) -> datetime | None:
        """Return the current deadline."""
        return next_feed_due(
            parse_datetime(self.data.get("last_fed")),
            self.data["location"],
            float(self.option(CONF_BENCH_INTERVAL, DEFAULT_BENCH_INTERVAL)),
            float(self.option(CONF_FRIDGE_INTERVAL, DEFAULT_FRIDGE_INTERVAL)),
        )

    def schedule_state(self) -> tuple[bool, bool]:
        """Return current due and due-soon states."""
        return schedule_state(
            self.next_due(),
            float(self.option(CONF_DUE_SOON, DEFAULT_DUE_SOON)),
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Refresh time-dependent entities and fire threshold events once."""
        is_due, is_due_soon = self.schedule_state()
        if is_due_soon and not self._was_due_soon:
            self._fire(EVENT_DUE_SOON)
        if is_due_soon:
            await self._async_send_reminder()
        if is_due:
            await self._async_send_overdue_reminder()
        if is_due and not self._was_due:
            self._fire(EVENT_OVERDUE)
        self._was_due = is_due
        self._was_due_soon = is_due_soon
        return self.data

    async def _async_send_reminder(self) -> None:
        """Send at most one configured notification for the current deadline."""
        targets = self.option(CONF_NOTIFICATION_TARGETS, [])
        if isinstance(targets, str):
            targets = [targets]
        due = self.next_due()
        if not targets or due is None:
            return
        due_key = due.isoformat()
        if self.data.get("last_reminder_for") == due_key:
            return
        data = {**self.data, "last_reminder_for": due_key}
        await self.store.save(data)
        self.async_set_updated_data(data)
        await self._async_notify(
            targets,
            (
                f"{self.entry.title} is due to be fed at "
                f"{dt_util.as_local(due).strftime('%-I:%M %p on %A, %-d %B')}."
            ),
        )

    async def _async_send_overdue_reminder(self) -> None:
        """Repeat an overdue notification every 30 minutes until fed."""
        targets = self.option(CONF_NOTIFICATION_TARGETS, [])
        if isinstance(targets, str):
            targets = [targets]
        due = self.next_due()
        if not targets or due is None:
            return
        now = dt_util.utcnow()
        last_sent = parse_datetime(self.data.get("last_overdue_reminder_at"))
        if last_sent and now - last_sent < timedelta(minutes=30):
            return
        data = {**self.data, "last_overdue_reminder_at": now.isoformat()}
        await self.store.save(data)
        self.async_set_updated_data(data)
        await self._async_notify(
            targets,
            f"{self.entry.title} is overdue for feeding. Feed it when you can.",
        )

    async def _async_notify(self, targets: list[str], message: str) -> None:
        """Send a reminder to the configured notification entities."""
        await self.hass.services.async_call(
            "notify",
            "send_message",
            {
                "title": "Sourdough feeding reminder",
                "message": message,
            },
            target={"entity_id": targets},
            blocking=False,
        )

    def _fire(self, event_type: str) -> None:
        """Fire an automation-friendly event."""
        self.hass.bus.async_fire(
            event_type,
            {
                "config_entry_id": self.entry.entry_id,
                "last_fed": self.data.get("last_fed"),
                "next_feed_due": self.next_due().isoformat() if self.next_due() else None,
                "location": self.data["location"],
            },
        )

    async def record_feed(self, fed_at: datetime | None = None) -> None:
        """Record a feed now or retrospectively."""
        fed_at = fed_at or dt_util.utcnow()
        if fed_at.tzinfo is None:
            fed_at = fed_at.replace(tzinfo=UTC)
        data = {
            **self.data,
            "last_fed": fed_at.isoformat(),
            "last_reminder_for": None,
            "last_overdue_reminder_at": None,
        }
        await self.store.save(data)
        self._was_due = False
        self._was_due_soon = False
        self.async_set_updated_data(data)
        self._fire(EVENT_FEED_RECORDED)

    async def set_location(self, location: str) -> None:
        """Change storage location and immediately recalculate the deadline."""
        if location == self.data["location"]:
            return
        data = {
            **self.data,
            "location": location,
            "location_changed_at": dt_util.utcnow().isoformat(),
        }
        await self.store.save(data)
        self.async_set_updated_data(data)
        self._was_due, self._was_due_soon = self.schedule_state()
        self._fire(EVENT_LOCATION_CHANGED)
