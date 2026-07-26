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
    CONF_CONFIRM_FEED,
    CONF_DUE_SOON,
    CONF_FRIDGE_INTERVAL,
    CONF_LAST_FED,
    CONF_LOCATION,
    CONF_NOTIFICATION_TARGETS,
    CONF_OVERDUE_INTERVAL,
    CONF_QUIET_END,
    CONF_QUIET_HOURS_ENABLED,
    CONF_QUIET_START,
    DEFAULT_BENCH_INTERVAL,
    DEFAULT_DUE_SOON,
    DEFAULT_FRIDGE_INTERVAL,
    DEFAULT_OVERDUE_INTERVAL,
    DEFAULT_QUIET_END,
    DEFAULT_QUIET_START,
    DOMAIN,
    DUPLICATE_FEED_SECONDS,
    EVENT_DUE_SOON,
    EVENT_FEED_RECORDED,
    EVENT_LOCATION_CHANGED,
    EVENT_OVERDUE,
    LOCATION_BENCH,
)
from .models import (
    human_duration,
    next_feed_due,
    overdue_notification_copy,
    parse_datetime,
    quiet_hours_active,
    schedule_state,
)
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
        if self.notifications_paused():
            return
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
            title=f"{self.entry.title} feeding due soon",
            notification_kind="due_soon",
        )

    async def _async_send_overdue_reminder(self) -> None:
        """Repeat overdue notifications at the configured interval until fed."""
        if self.notifications_paused():
            return
        targets = self.option(CONF_NOTIFICATION_TARGETS, [])
        if isinstance(targets, str):
            targets = [targets]
        due = self.next_due()
        if not targets or due is None:
            return
        now = dt_util.utcnow()
        last_sent = parse_datetime(self.data.get("last_overdue_reminder_at"))
        interval = float(
            self.option(CONF_OVERDUE_INTERVAL, DEFAULT_OVERDUE_INTERVAL)
        )
        if last_sent and now - last_sent < timedelta(minutes=interval):
            return
        data = {**self.data, "last_overdue_reminder_at": now.isoformat()}
        await self.store.save(data)
        self.async_set_updated_data(data)
        hours_overdue = max(0.0, (now - due).total_seconds() / 3600)
        title, message = overdue_notification_copy(
            self.entry.title, hours_overdue
        )
        await self._async_notify(
            targets,
            message,
            title=title,
            notification_kind="overdue",
        )

    def notifications_paused(self) -> bool:
        """Return whether snooze or quiet hours currently suppress reminders."""
        now = dt_util.utcnow()
        snoozed_until = parse_datetime(self.data.get("snoozed_until"))
        if snoozed_until and now < snoozed_until:
            return True
        return quiet_hours_active(
            dt_util.as_local(now),
            bool(self.option(CONF_QUIET_HOURS_ENABLED, False)),
            self.option(CONF_QUIET_START, DEFAULT_QUIET_START),
            self.option(CONF_QUIET_END, DEFAULT_QUIET_END),
        )

    async def _async_notify(
        self,
        targets: list[str],
        message: str,
        *,
        title: str,
        notification_kind: str,
        actionable: bool = True,
        record_reminder: bool = True,
    ) -> None:
        """Send a reminder to the configured notification entities."""
        mobile_targets: list[str] = []
        generic_targets: list[str] = []
        for entity_id in targets:
            object_id = entity_id.partition(".")[2]
            if object_id.startswith("mobile_app_") and self.hass.services.has_service(
                "notify", object_id
            ):
                mobile_targets.append(object_id)
            else:
                generic_targets.append(entity_id)

        actions = []
        if actionable:
            actions = [
                {"action": self.feed_action, "title": "Fed now"},
                {
                    "action": self.snooze_action,
                    "title": (
                        f"Snooze {human_duration(float(self.data['snooze_hours']))}"
                    ),
                },
            ]
        for service in mobile_targets:
            payload: dict[str, Any] = {
                "title": title,
                "message": message,
                "data": {
                    "tag": (
                        f"sourdough_{notification_kind}_{self.entry.entry_id}"
                    )
                },
            }
            if actions:
                payload["data"]["actions"] = actions
            await self.hass.services.async_call(
                "notify", service, payload, blocking=False
            )
        if generic_targets:
            await self.hass.services.async_call(
                "notify",
                "send_message",
                {
                    "title": title,
                    "message": message,
                },
                target={"entity_id": generic_targets},
                blocking=False,
            )
        if record_reminder:
            data = {
                **self.data,
                "last_reminder_sent_at": dt_util.utcnow().isoformat(),
            }
            await self.store.save(data)
            self.async_set_updated_data(data)

    @property
    def feed_action(self) -> str:
        """Return this starter's mobile notification feed action ID."""
        return f"SOURDOUGH_FED_{self.entry.entry_id}"

    @property
    def snooze_action(self) -> str:
        """Return this starter's mobile notification snooze action ID."""
        return f"SOURDOUGH_SNOOZE_{self.entry.entry_id}"

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

    async def record_feed(
        self,
        fed_at: datetime | None = None,
        *,
        protect_duplicate: bool = False,
    ) -> bool:
        """Record a feed now or retrospectively."""
        now = dt_util.utcnow()
        if protect_duplicate:
            previous = parse_datetime(self.data.get("last_fed"))
            if previous:
                elapsed = now - previous
                if timedelta(0) <= elapsed < timedelta(
                    seconds=DUPLICATE_FEED_SECONDS
                ):
                    return False
        fed_at = fed_at or now
        if fed_at.tzinfo is None:
            fed_at = fed_at.replace(tzinfo=UTC)
        data = {
            **self.data,
            "last_fed": fed_at.isoformat(),
            "last_reminder_for": None,
            "last_overdue_reminder_at": None,
            "snoozed_until": None,
        }
        await self.store.save(data)
        self._was_due = False
        self._was_due_soon = False
        self.async_set_updated_data(data)
        self._fire(EVENT_FEED_RECORDED)
        if bool(self.option(CONF_CONFIRM_FEED, False)):
            targets = self.option(CONF_NOTIFICATION_TARGETS, [])
            if isinstance(targets, str):
                targets = [targets]
            if targets:
                await self._async_notify(
                    targets,
                    f"{self.entry.title} was recorded as fed.",
                    title=f"{self.entry.title} feed recorded",
                    notification_kind="confirmation",
                    actionable=False,
                    record_reminder=False,
                )
        return True

    async def set_snooze_duration(self, hours: str) -> None:
        """Set the duration used by the snooze button and notification action."""
        data = {**self.data, "snooze_hours": hours}
        await self.store.save(data)
        self.async_set_updated_data(data)

    async def snooze(self) -> None:
        """Pause reminders for the selected duration."""
        until = dt_util.utcnow() + timedelta(hours=float(self.data["snooze_hours"]))
        data = {**self.data, "snoozed_until": until.isoformat()}
        await self.store.save(data)
        self.async_set_updated_data(data)

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
