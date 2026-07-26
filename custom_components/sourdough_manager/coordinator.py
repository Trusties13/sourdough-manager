"""Runtime coordinator."""
from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from .const import (
    CONF_AUDIO_ENABLED,
    CONF_AUDIO_INTERVAL,
    CONF_AUDIO_LEAD_TIME,
    CONF_AUDIO_TARGETS,
    CONF_AUDIO_TTS_ENTITY,
    CONF_AUDIO_VOLUME,
    CONF_BENCH_INTERVAL,
    CONF_CONFIRM_FEED,
    CONF_DUE_SOON,
    CONF_FRIDGE_INTERVAL,
    CONF_LAST_FED,
    CONF_LIGHT_TARGETS,
    CONF_LIGHT_COLOR,
    CONF_LOCATION,
    CONF_NOTIFICATION_TARGETS,
    CONF_OVERDUE_INTERVAL,
    CONF_QUIET_END,
    CONF_QUIET_HOURS_ENABLED,
    CONF_QUIET_START,
    DEFAULT_AUDIO_INTERVAL,
    DEFAULT_AUDIO_LEAD_TIME,
    DEFAULT_AUDIO_VOLUME,
    DEFAULT_BENCH_INTERVAL,
    DEFAULT_DUE_SOON,
    DEFAULT_FRIDGE_INTERVAL,
    DEFAULT_LIGHT_COLOR,
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
    audio_reminder_due,
    human_duration,
    light_restore_data,
    next_feed_due,
    overdue_notification_copy,
    parse_datetime,
    quiet_hours_active,
    schedule_state,
)
from .storage import StarterStore

_LOGGER = logging.getLogger(__name__)
COLOR_MODES = {"hs", "xy", "rgb", "rgbw", "rgbww"}


class SourdoughCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Own scheduling state and mutations for one starter."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(
            hass,
            logger=_LOGGER,
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
        reminder_sent = False
        if is_due_soon and not self._was_due_soon:
            self._fire(EVENT_DUE_SOON)
        if is_due_soon:
            reminder_sent = await self._async_send_reminder()
        if is_due:
            reminder_sent = (
                await self._async_send_overdue_reminder() or reminder_sent
            )
        reminder_sent = (
            await self._async_send_audio_reminder() or reminder_sent
        )
        if reminder_sent:
            await self._async_send_light_reminder()
        if is_due and not self._was_due:
            self._fire(EVENT_OVERDUE)
        self._was_due = is_due
        self._was_due_soon = is_due_soon
        return self.data

    async def _async_send_reminder(self) -> bool:
        """Send at most one configured notification for the current deadline."""
        if self.notifications_paused():
            return False
        targets = self.option(CONF_NOTIFICATION_TARGETS, [])
        if isinstance(targets, str):
            targets = [targets]
        due = self.next_due()
        if not targets or due is None:
            return False
        due_key = due.isoformat()
        if self.data.get("last_reminder_for") == due_key:
            return False
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
        return True

    async def _async_send_overdue_reminder(self) -> bool:
        """Repeat overdue notifications at the configured interval until fed."""
        if self.notifications_paused():
            return False
        targets = self.option(CONF_NOTIFICATION_TARGETS, [])
        if isinstance(targets, str):
            targets = [targets]
        due = self.next_due()
        if not targets or due is None:
            return False
        now = dt_util.utcnow()
        last_sent = parse_datetime(self.data.get("last_overdue_reminder_at"))
        interval = float(
            self.option(CONF_OVERDUE_INTERVAL, DEFAULT_OVERDUE_INTERVAL)
        )
        if last_sent and now - last_sent < timedelta(minutes=interval):
            return False
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
        return True

    async def _async_send_audio_reminder(self) -> bool:
        """Speak reminders on configured media players at its own cadence."""
        if not bool(self.option(CONF_AUDIO_ENABLED, False)):
            return False
        if self.notifications_paused():
            return False
        tts_entity = self.option(CONF_AUDIO_TTS_ENTITY, None)
        targets = self.option(CONF_AUDIO_TARGETS, [])
        if isinstance(targets, str):
            targets = [targets]
        due = self.next_due()
        if not tts_entity or not targets or due is None:
            return False
        now = dt_util.utcnow()
        if not audio_reminder_due(
            now,
            due,
            float(
                self.option(
                    CONF_AUDIO_LEAD_TIME, DEFAULT_AUDIO_LEAD_TIME
                )
            ),
            parse_datetime(self.data.get("last_audio_reminder_at")),
            float(self.option(CONF_AUDIO_INTERVAL, DEFAULT_AUDIO_INTERVAL)),
        ):
            return False
        if now < due:
            remaining = (due - now).total_seconds() / 3600
            message = (
                f"{self.entry.title} will be due for feeding in "
                f"{human_duration(remaining)}."
            )
        else:
            hours_overdue = max(0.0, (now - due).total_seconds() / 3600)
            _, message = overdue_notification_copy(
                self.entry.title, hours_overdue
            )
        spoken = False
        for media_player in targets:
            state = self.hass.states.get(media_player)
            if state is None or state.state in {"unavailable", "unknown"}:
                continue
            self.hass.async_create_task(
                self._async_speak_at_configured_volume(
                    tts_entity, media_player, message
                ),
                f"{DOMAIN}_audio_reminder_{media_player}",
            )
            spoken = True
        if spoken:
            data = {**self.data, "last_audio_reminder_at": now.isoformat()}
            await self.store.save(data)
            self.async_set_updated_data(data)
        return spoken

    async def _async_send_light_reminder(
        self, *, ignore_pause: bool = False
    ) -> None:
        """Accompany a sent push or audio reminder with a light flash."""
        if not ignore_pause and self.notifications_paused():
            return
        targets = self.option(CONF_LIGHT_TARGETS, [])
        if isinstance(targets, str):
            targets = [targets]
        if not targets:
            return
        now = dt_util.utcnow()
        flashed = False
        for light in targets:
            state = self.hass.states.get(light)
            if state is None or state.state in {"unavailable", "unknown"}:
                continue
            supported = set(state.attributes.get("supported_color_modes", []))
            if not supported.intersection(COLOR_MODES):
                continue
            try:
                await self._async_flash_light(
                    light,
                    state.state == "on",
                    light_restore_data(dict(state.attributes)),
                )
                flashed = True
            except HomeAssistantError:
                _LOGGER.exception("Unable to flash reminder light %s", light)
        if flashed:
            data = {**self.data, "last_light_reminder_at": now.isoformat()}
            await self.store.save(data)
            self.async_set_updated_data(data)

    async def test_push_reminder(self) -> None:
        """Send a test push reminder and accompany it with the light alert."""
        targets = self.option(CONF_NOTIFICATION_TARGETS, [])
        if isinstance(targets, str):
            targets = [targets]
        if not targets:
            raise HomeAssistantError(
                "No notification targets are configured for this starter"
            )
        title, message = overdue_notification_copy(self.entry.title, 1)
        await self._async_notify(
            targets,
            f"Test reminder. {message}",
            title=f"TEST — {title}",
            notification_kind="test",
            actionable=False,
            record_reminder=False,
        )
        await self._async_send_light_reminder(ignore_pause=True)

    async def test_audio_reminder(self) -> None:
        """Speak a test reminder and accompany it with the light alert."""
        tts_entity = self.option(CONF_AUDIO_TTS_ENTITY, None)
        targets = self.option(CONF_AUDIO_TARGETS, [])
        if isinstance(targets, str):
            targets = [targets]
        if not tts_entity or not targets:
            raise HomeAssistantError(
                "A text-to-speech provider and audio target are required"
            )
        _, overdue_message = overdue_notification_copy(self.entry.title, 1)
        spoken = False
        for media_player in targets:
            state = self.hass.states.get(media_player)
            if state is None or state.state in {"unavailable", "unknown"}:
                continue
            self.hass.async_create_task(
                self._async_speak_at_configured_volume(
                    tts_entity,
                    media_player,
                    f"Test reminder. {overdue_message}",
                ),
                f"{DOMAIN}_test_audio_reminder_{media_player}",
            )
            spoken = True
        if not spoken:
            raise HomeAssistantError(
                "None of the configured audio targets are available"
            )
        await self._async_send_light_reminder(ignore_pause=True)

    async def _async_speak_at_configured_volume(
        self,
        tts_entity: str,
        media_player: str,
        message: str,
    ) -> None:
        """Temporarily set announcement volume, speak, then restore it."""
        state = self.hass.states.get(media_player)
        previous_volume = (
            state.attributes.get("volume_level") if state is not None else None
        )
        announcement_volume = (
            float(
                self.option(CONF_AUDIO_VOLUME, DEFAULT_AUDIO_VOLUME)
            )
            / 100
        )
        try:
            await self.hass.services.async_call(
                "media_player",
                "volume_set",
                {"volume_level": announcement_volume},
                target={"entity_id": media_player},
                blocking=True,
            )
            await self.hass.services.async_call(
                "tts",
                "speak",
                {
                    "media_player_entity_id": media_player,
                    "message": message,
                    "cache": True,
                },
                target={"entity_id": tts_entity},
                blocking=False,
            )
            for _ in range(40):
                current = self.hass.states.get(media_player)
                if current is not None and current.state == "playing":
                    break
                await asyncio.sleep(0.25)
            for _ in range(240):
                current = self.hass.states.get(media_player)
                if current is None or current.state != "playing":
                    break
                await asyncio.sleep(0.5)
        finally:
            if previous_volume is not None:
                await self.hass.services.async_call(
                    "media_player",
                    "volume_set",
                    {"volume_level": previous_volume},
                    target={"entity_id": media_player},
                    blocking=True,
                )

    async def _async_flash_light(
        self,
        entity_id: str,
        was_on: bool,
        restore_data: dict[str, Any],
    ) -> None:
        """Flash one light three times and restore its prior settings."""
        flash_color = list(
            self.option(CONF_LIGHT_COLOR, DEFAULT_LIGHT_COLOR)
        )
        try:
            for _ in range(3):
                await self.hass.services.async_call(
                    "light",
                    "turn_on",
                    {
                        "rgb_color": flash_color,
                        "brightness": 255,
                        "transition": 0,
                    },
                    target={"entity_id": entity_id},
                    blocking=True,
                )
                await asyncio.sleep(0.35)
                if was_on:
                    await self.hass.services.async_call(
                        "light",
                        "turn_on",
                        {**restore_data, "transition": 0},
                        target={"entity_id": entity_id},
                        blocking=True,
                    )
                else:
                    await self.hass.services.async_call(
                        "light",
                        "turn_off",
                        {"transition": 0},
                        target={"entity_id": entity_id},
                        blocking=True,
                    )
                await asyncio.sleep(0.25)
        finally:
            if was_on:
                await self.hass.services.async_call(
                    "light",
                    "turn_on",
                    {**restore_data, "transition": 0},
                    target={"entity_id": entity_id},
                    blocking=True,
                )
            else:
                if restore_data:
                    await self.hass.services.async_call(
                        "light",
                        "turn_on",
                        {**restore_data, "transition": 0},
                        target={"entity_id": entity_id},
                        blocking=True,
                    )
                    await asyncio.sleep(0.05)
                await self.hass.services.async_call(
                    "light",
                    "turn_off",
                    {"transition": 0},
                    target={"entity_id": entity_id},
                    blocking=True,
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
            "last_audio_reminder_at": None,
            "last_light_reminder_at": None,
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
