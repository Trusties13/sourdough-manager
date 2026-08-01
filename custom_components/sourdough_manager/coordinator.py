"""Runtime coordinator."""
from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import issue_registry as ir
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
    CONF_BENCH_PREFERRED_TIME,
    CONF_CONFIRM_FEED,
    CONF_DISRUPTIVE_MAX_COUNT,
    CONF_DISRUPTIVE_MAX_OVERDUE_HOURS,
    CONF_DUE_SOON,
    CONF_FRIDGE_INTERVAL,
    CONF_FRIDGE_PREFERRED_TIME,
    CONF_HOLIDAY_MODE_ENTITY,
    CONF_HOLIDAY_MODE_POLICY,
    CONF_LAST_FED,
    CONF_LIGHT_COLOR,
    CONF_LIGHT_FLASH_COUNT,
    CONF_LIGHT_GAP_SECONDS,
    CONF_LIGHT_PULSE_SECONDS,
    CONF_LIGHT_TARGETS,
    CONF_LOCATION,
    CONF_NOTIFICATION_TARGETS,
    CONF_OCCUPANCY_AUDIO_ONLY,
    CONF_OCCUPANCY_ENTITY,
    CONF_OVERDUE_INTERVAL,
    CONF_PREFERRED_TIME,
    CONF_PREFERRED_TIME_ENABLED,
    CONF_QUIET_END,
    CONF_QUIET_HOURS_ENABLED,
    CONF_QUIET_START,
    DEFAULT_AUDIO_INTERVAL,
    DEFAULT_AUDIO_LEAD_TIME,
    DEFAULT_AUDIO_VOLUME,
    DEFAULT_BENCH_INTERVAL,
    DEFAULT_DISRUPTIVE_MAX_COUNT,
    DEFAULT_DISRUPTIVE_MAX_OVERDUE_HOURS,
    DEFAULT_DUE_SOON,
    DEFAULT_FRIDGE_INTERVAL,
    DEFAULT_HOLIDAY_MODE_ENTITY,
    DEFAULT_HOLIDAY_MODE_POLICY,
    DEFAULT_LIGHT_COLOR,
    DEFAULT_LIGHT_FLASH_COUNT,
    DEFAULT_LIGHT_GAP_SECONDS,
    DEFAULT_LIGHT_PULSE_SECONDS,
    DEFAULT_OCCUPANCY_ENTITY,
    DEFAULT_OVERDUE_INTERVAL,
    DEFAULT_PREFERRED_TIME,
    DEFAULT_QUIET_END,
    DEFAULT_QUIET_START,
    DOMAIN,
    DUPLICATE_FEED_SECONDS,
    EVENT_DEADLINE_DELAYED,
    EVENT_DUE_SOON,
    EVENT_FEED_RECORDED,
    EVENT_LOCATION_CHANGED,
    EVENT_OVERDUE,
    LOCATION_BENCH,
    LOCATION_FRIDGE,
    MAX_FEED_HISTORY,
)
from .models import (
    align_deadline_to_preferred_time,
    audio_reminder_due,
    due_today_or_overdue,
    human_duration,
    light_restore_data,
    next_feed_due,
    overdue_notification_copy,
    parse_clock,
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
        self._event_listeners: list[Any] = []

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
        self._update_configuration_issue()

    def next_due(self) -> datetime | None:
        """Return the current deadline."""
        override = parse_datetime(self.data.get("deadline_override"))
        if override is not None:
            return override
        due = next_feed_due(
            parse_datetime(self.data.get("last_fed")),
            self.data["location"],
            float(self.option(CONF_BENCH_INTERVAL, DEFAULT_BENCH_INTERVAL)),
            float(self.option(CONF_FRIDGE_INTERVAL, DEFAULT_FRIDGE_INTERVAL)),
        )
        if due is None or not bool(
            self.option(CONF_PREFERRED_TIME_ENABLED, False)
        ):
            return due
        local_due = dt_util.as_local(due)
        preferred_key = (
            CONF_FRIDGE_PREFERRED_TIME
            if self.data["location"] == LOCATION_FRIDGE
            else CONF_BENCH_PREFERRED_TIME
        )
        aligned = align_deadline_to_preferred_time(
            local_due,
            self.option(
                preferred_key,
                self.option(CONF_PREFERRED_TIME, DEFAULT_PREFERRED_TIME),
            ),
        )
        return dt_util.as_utc(aligned) if aligned else None

    def delay_available(self) -> bool:
        """Return whether a deadline may be delayed today."""
        due = self.next_due()
        return due_today_or_overdue(
            dt_util.as_local(due) if due else None,
            dt_util.now(),
        )

    def due_today(self) -> bool:
        """Return whether the deadline falls on the current local date."""
        due = self.next_due()
        return bool(
            due
            and dt_util.as_local(due).date() == dt_util.now().date()
        )

    def holiday_mode_active(self) -> bool:
        """Return whether the configured external holiday sensor is on."""
        entity_id = self.option(
            CONF_HOLIDAY_MODE_ENTITY, DEFAULT_HOLIDAY_MODE_ENTITY
        )
        return bool(entity_id) and self.hass.states.is_state(entity_id, "on")

    def holiday_policy(self) -> str:
        """Return how Holiday Mode affects reminders."""
        return str(
            self.option(CONF_HOLIDAY_MODE_POLICY, DEFAULT_HOLIDAY_MODE_POLICY)
        )

    def channel_enabled(self, channel: str) -> bool:
        """Return whether one reminder channel is enabled."""
        stored = self.data.get(f"{channel}_reminders_enabled")
        if stored is not None:
            return bool(stored)
        if channel == "audio":
            return bool(self.option(CONF_AUDIO_ENABLED, False))
        return True

    def occupancy_allows_audio(self) -> bool:
        """Return whether occupancy settings permit spoken reminders."""
        if not bool(self.option(CONF_OCCUPANCY_AUDIO_ONLY, False)):
            return True
        entity_id = self.option(CONF_OCCUPANCY_ENTITY, DEFAULT_OCCUPANCY_ENTITY)
        return bool(entity_id) and self.hass.states.is_state(entity_id, "on")

    def disruptive_reminders_allowed(self) -> bool:
        """Return whether audio and light escalation may continue."""
        if self.data.get("silent_until_next_feed", False):
            return False
        maximum = int(
            self.option(CONF_DISRUPTIVE_MAX_COUNT, DEFAULT_DISRUPTIVE_MAX_COUNT)
        )
        if maximum and int(self.data.get("disruptive_reminder_count", 0)) >= maximum:
            return False
        due = self.next_due()
        maximum_hours = float(
            self.option(
                CONF_DISRUPTIVE_MAX_OVERDUE_HOURS,
                DEFAULT_DISRUPTIVE_MAX_OVERDUE_HOURS,
            )
        )
        return not (
            maximum_hours
            and due is not None
            and dt_util.utcnow() - due >= timedelta(hours=maximum_hours)
        )

    def schedule_status(self) -> str:
        """Return a concise dashboard-friendly schedule state."""
        if not bool(self.data.get("reminders_enabled", True)):
            return "reminders_disabled"
        if self.data.get("silent_until_next_feed", False):
            return "silent_until_feed"
        if self._snoozed():
            return "snoozed"
        if self._quiet_hours_active():
            return "quiet_hours"
        if (
            self.holiday_mode_active()
            and self.holiday_policy() == "suppress_push"
        ):
            return "holiday_push_suppressed"
        if self.holiday_mode_active() and self.holiday_policy() == "suppress_all":
            return "holiday"
        is_due, is_due_soon = self.schedule_state()
        if is_due:
            return "overdue"
        due = self.next_due()
        if due and self.due_today():
            return "due_today"
        if is_due_soon:
            return "due_soon"
        return "on_schedule"

    def schedule_state(self) -> tuple[bool, bool]:
        """Return current due and due-soon states."""
        return schedule_state(
            self.next_due(),
            float(self.option(CONF_DUE_SOON, DEFAULT_DUE_SOON)),
        )

    def next_reminder_times(self) -> dict[str, datetime | None]:
        """Return the next calculable push and audio reminder times."""
        due = self.next_due()
        now = dt_util.utcnow()
        push_at: datetime | None = None
        audio_at: datetime | None = None
        if due is None or self.notifications_paused():
            return {"push": None, "audio": None}
        if self.channel_enabled("push") and not self.push_notifications_paused():
            if now < due:
                early = due - timedelta(
                    hours=float(self.option(CONF_DUE_SOON, DEFAULT_DUE_SOON))
                )
                if self.data.get("last_reminder_for") != due.isoformat():
                    push_at = max(now, early)
                else:
                    push_at = due
            else:
                last_push = parse_datetime(
                    self.data.get("last_overdue_reminder_at")
                )
                push_at = max(
                    now,
                    (last_push or now)
                    + timedelta(
                        minutes=float(
                            self.option(
                                CONF_OVERDUE_INTERVAL,
                                DEFAULT_OVERDUE_INTERVAL,
                            )
                        )
                    ),
                ) if last_push else now
        if (
            self.channel_enabled("audio")
            and self.occupancy_allows_audio()
            and self.disruptive_reminders_allowed()
        ):
            start = due - timedelta(
                hours=float(
                    self.option(CONF_AUDIO_LEAD_TIME, DEFAULT_AUDIO_LEAD_TIME)
                )
            )
            last_audio = parse_datetime(self.data.get("last_audio_reminder_at"))
            audio_at = max(now, start)
            if last_audio:
                audio_at = max(
                    audio_at,
                    last_audio
                    + timedelta(
                        minutes=float(
                            self.option(CONF_AUDIO_INTERVAL, DEFAULT_AUDIO_INTERVAL)
                        )
                    ),
                )
        return {"push": push_at, "audio": audio_at}

    async def _async_update_data(self) -> dict[str, Any]:
        """Refresh time-dependent entities and fire threshold events once."""
        self._update_configuration_issue()
        is_due, is_due_soon = self.schedule_state()
        reminder_sent = False
        if is_due_soon and not self._was_due_soon:
            self._fire(EVENT_DUE_SOON)
        if is_due_soon:
            reminder_sent = await self._async_send_reminder()
        if is_due:
            await self._async_record_missed_deadline()
            reminder_sent = (
                await self._async_send_overdue_reminder() or reminder_sent
            )
        audio_sent = await self._async_send_audio_reminder()
        reminder_sent = audio_sent or reminder_sent
        light_sent = False
        if reminder_sent:
            light_sent = await self._async_send_light_reminder()
        if audio_sent or light_sent:
            data = {
                **self.data,
                "disruptive_reminder_count": int(
                    self.data.get("disruptive_reminder_count", 0)
                )
                + 1,
            }
            await self.store.save(data)
            self.async_set_updated_data(data)
        if is_due and not self._was_due:
            self._fire(EVENT_OVERDUE)
        self._was_due = is_due
        self._was_due_soon = is_due_soon
        return self.data

    async def _async_record_missed_deadline(self) -> None:
        """Count each deadline once when it first becomes overdue."""
        due = self.next_due()
        if due is None:
            return
        due_key = due.isoformat()
        if self.data.get("missed_deadline_for") == due_key:
            return
        data = {
            **self.data,
            "missed_feed_count": int(self.data.get("missed_feed_count", 0)) + 1,
            "missed_deadline_for": due_key,
        }
        await self.store.save(data)
        self.async_set_updated_data(data)

    def invalid_targets(self) -> list[str]:
        """Return configured entities that no longer exist."""
        registry = er.async_get(self.hass)
        configured: list[str] = []
        for key in (
            CONF_NOTIFICATION_TARGETS,
            CONF_AUDIO_TARGETS,
            CONF_LIGHT_TARGETS,
        ):
            value = self.option(key, [])
            configured.extend([value] if isinstance(value, str) else value)
        tts = self.option(CONF_AUDIO_TTS_ENTITY, None)
        if tts:
            configured.append(tts)
        occupancy = self.option(CONF_OCCUPANCY_ENTITY, DEFAULT_OCCUPANCY_ENTITY)
        if bool(self.option(CONF_OCCUPANCY_AUDIO_ONLY, False)) and occupancy:
            configured.append(occupancy)
        holiday = self.option(
            CONF_HOLIDAY_MODE_ENTITY, DEFAULT_HOLIDAY_MODE_ENTITY
        )
        holiday_explicit = (
            CONF_HOLIDAY_MODE_ENTITY in self.entry.options
            or CONF_HOLIDAY_MODE_ENTITY in self.entry.data
        )
        if holiday and (
            holiday_explicit or self.hass.states.get(holiday) is not None
        ):
            configured.append(holiday)
        return sorted(
            {
                entity_id
                for entity_id in configured
                if registry.async_get(entity_id) is None
            }
        )

    def _update_configuration_issue(self) -> None:
        """Create or clear a repair issue for deleted target entities."""
        issue_id = f"invalid_targets_{self.entry.entry_id}"
        invalid = self.invalid_targets()
        if not invalid:
            ir.async_delete_issue(self.hass, DOMAIN, issue_id)
            return
        ir.async_create_issue(
            self.hass,
            DOMAIN,
            issue_id,
            is_fixable=False,
            severity=ir.IssueSeverity.WARNING,
            translation_key="invalid_targets",
            translation_placeholders={
                "starter": self.entry.title,
                "targets": ", ".join(invalid),
            },
        )

    async def _async_send_reminder(self) -> bool:
        """Send at most one configured notification for the current deadline."""
        if not self.channel_enabled("push"):
            return False
        if self.push_notifications_paused():
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
        if not self.channel_enabled("push"):
            return False
        if self.push_notifications_paused():
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
        if not self.channel_enabled("audio"):
            return False
        if self.notifications_paused():
            return False
        if not self.occupancy_allows_audio():
            return False
        if not self.disruptive_reminders_allowed():
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
    ) -> bool:
        """Accompany a sent push or audio reminder with a light flash."""
        if not ignore_pause and self.notifications_paused():
            return False
        if not ignore_pause and not self.channel_enabled("light"):
            return False
        if not ignore_pause and not self.disruptive_reminders_allowed():
            return False
        targets = self.option(CONF_LIGHT_TARGETS, [])
        if isinstance(targets, str):
            targets = [targets]
        if not targets:
            return False
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
            data = {
                **self.data,
                "last_light_reminder_at": now.isoformat(),
            }
            await self.store.save(data)
            self.async_set_updated_data(data)
        return flashed

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
        flash_count = int(
            self.option(
                CONF_LIGHT_FLASH_COUNT, DEFAULT_LIGHT_FLASH_COUNT
            )
        )
        pulse_seconds = float(
            self.option(
                CONF_LIGHT_PULSE_SECONDS, DEFAULT_LIGHT_PULSE_SECONDS
            )
        )
        gap_seconds = float(
            self.option(
                CONF_LIGHT_GAP_SECONDS, DEFAULT_LIGHT_GAP_SECONDS
            )
        )
        try:
            for _ in range(flash_count):
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
                await asyncio.sleep(pulse_seconds)
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
                await asyncio.sleep(gap_seconds)
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

    def _snoozed(self) -> bool:
        """Return whether the reminder cycle is currently snoozed."""
        snoozed_until = parse_datetime(self.data.get("snoozed_until"))
        return bool(snoozed_until and dt_util.utcnow() < snoozed_until)

    def _quiet_hours_active(self) -> bool:
        """Return whether configured quiet hours are active."""
        now = dt_util.utcnow()
        return quiet_hours_active(
            dt_util.as_local(now),
            bool(self.option(CONF_QUIET_HOURS_ENABLED, False)),
            self.option(CONF_QUIET_START, DEFAULT_QUIET_START),
            self.option(CONF_QUIET_END, DEFAULT_QUIET_END),
        )

    def notifications_paused(self) -> bool:
        """Return whether all scheduled reminder channels are paused."""
        if not bool(self.data.get("reminders_enabled", True)):
            return True
        if (
            self.holiday_mode_active()
            and self.holiday_policy() == "suppress_all"
        ):
            return True
        return self._snoozed() or self._quiet_hours_active()

    def push_notifications_paused(self) -> bool:
        """Return whether scheduled push notifications are paused."""
        if self.notifications_paused():
            return True
        return (
            self.holiday_mode_active()
            and self.holiday_policy() == "suppress_push"
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
        event_data = {
            "config_entry_id": self.entry.entry_id,
            "last_fed": self.data.get("last_fed"),
            "next_feed_due": self.next_due().isoformat() if self.next_due() else None,
            "location": self.data["location"],
        }
        self.hass.bus.async_fire(
            event_type,
            event_data,
        )
        short_type = {
            EVENT_FEED_RECORDED: "feed_recorded",
            EVENT_DUE_SOON: "due_soon",
            EVENT_OVERDUE: "overdue",
            EVENT_LOCATION_CHANGED: "location_changed",
            EVENT_DEADLINE_DELAYED: "deadline_delayed",
        }[event_type]
        now = dt_util.utcnow().isoformat()
        self.data["last_event_type"] = short_type
        self.data["last_event_at"] = now
        for listener in self._event_listeners:
            listener(short_type, event_data)

    def add_event_listener(self, listener) -> Any:
        """Subscribe an event entity to starter events."""
        self._event_listeners.append(listener)

        def remove_listener() -> None:
            if listener in self._event_listeners:
                self._event_listeners.remove(listener)

        return remove_listener

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
        history = list(self.data.get("feed_history", []))
        history.append(
            {
                "fed_at": fed_at.isoformat(),
                "location": self.data["location"],
            }
        )
        data = {
            **self.data,
            "last_fed": fed_at.isoformat(),
            "deadline_override": None,
            "feed_history": history[-MAX_FEED_HISTORY:],
            "last_reminder_for": None,
            "last_overdue_reminder_at": None,
            "snoozed_until": None,
            "last_audio_reminder_at": None,
            "last_light_reminder_at": None,
            "silent_until_next_feed": False,
            "disruptive_reminder_count": 0,
            "missed_deadline_for": None,
        }
        await self.store.save(data)
        self._was_due = False
        self._was_due_soon = False
        self.async_set_updated_data(data)
        self._fire(EVENT_FEED_RECORDED)
        await self._async_clear_overdue_notification()
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

    async def set_delay_option(self, option: str) -> None:
        """Select the one-off delay used by the delay button."""
        data = {**self.data, "delay_option": option}
        await self.store.save(data)
        self.async_set_updated_data(data)

    async def delay_next_feed(self) -> None:
        """Move the current deadline by the selected one-off delay."""
        if not self.delay_available():
            raise HomeAssistantError(
                "The next feeding can only be delayed on its due date or while overdue"
            )
        current_due = self.next_due()
        if current_due is None:
            raise HomeAssistantError("Record a feed before delaying its deadline")
        option = self.data.get("delay_option", "1")
        if option == "tomorrow_morning":
            local_now = dt_util.now()
            preferred_key = (
                CONF_FRIDGE_PREFERRED_TIME
                if self.data["location"] == LOCATION_FRIDGE
                else CONF_BENCH_PREFERRED_TIME
            )
            preferred = self.option(
                preferred_key,
                self.option(CONF_PREFERRED_TIME, DEFAULT_PREFERRED_TIME),
            )
            clock = parse_clock(preferred)
            delayed_local = datetime.combine(
                local_now.date() + timedelta(days=1), clock
            ).replace(tzinfo=dt_util.get_default_time_zone())
            delayed = dt_util.as_utc(delayed_local)
        else:
            delayed = current_due + timedelta(hours=float(option))
        await self.set_next_feed_due(delayed)

    async def set_next_feed_due(self, due_at: datetime) -> None:
        """Set a one-off explicit next-feed deadline."""
        if not self.delay_available():
            raise HomeAssistantError(
                "The next feeding can only be changed on its due date or while overdue"
            )
        if due_at.tzinfo is None:
            due_at = due_at.replace(tzinfo=dt_util.get_default_time_zone())
        due_at = dt_util.as_utc(due_at)
        data = {
            **self.data,
            "deadline_override": due_at.isoformat(),
            "last_reminder_for": None,
            "last_overdue_reminder_at": None,
            "snoozed_until": None,
            "last_audio_reminder_at": None,
            "last_light_reminder_at": None,
            "disruptive_reminder_count": 0,
            "missed_deadline_for": None,
        }
        await self.store.save(data)
        self._was_due = False
        self._was_due_soon = False
        self.async_set_updated_data(data)
        self._fire(EVENT_DEADLINE_DELAYED)

    async def record_feed_in_fridge(self) -> bool:
        """Move the starter to the fridge and record a feed in one action."""
        if self.data["location"] != LOCATION_FRIDGE:
            await self.set_location(LOCATION_FRIDGE)
        return await self.record_feed(protect_duplicate=True)

    async def _async_clear_overdue_notification(self) -> None:
        """Remove this starter's tagged overdue Companion App alert."""
        targets = self.option(CONF_NOTIFICATION_TARGETS, [])
        if isinstance(targets, str):
            targets = [targets]
        tag = f"sourdough_overdue_{self.entry.entry_id}"
        for entity_id in targets:
            service = entity_id.partition(".")[2]
            if not service.startswith("mobile_app_"):
                continue
            if not self.hass.services.has_service("notify", service):
                continue
            await self.hass.services.async_call(
                "notify",
                service,
                {
                    "message": "clear_notification",
                    "data": {"tag": tag},
                },
                blocking=False,
            )

    async def set_reminders_enabled(self, enabled: bool) -> None:
        """Enable or disable every scheduled reminder channel."""
        data = {**self.data, "reminders_enabled": enabled}
        await self.store.save(data)
        self.async_set_updated_data(data)

    async def set_channel_enabled(self, channel: str, enabled: bool) -> None:
        """Enable or disable one scheduled reminder channel."""
        data = {**self.data, f"{channel}_reminders_enabled": enabled}
        await self.store.save(data)
        self.async_set_updated_data(data)

    async def set_silent_until_next_feed(self, enabled: bool) -> None:
        """Mute or restore disruptive reminders for the current cycle."""
        data = {**self.data, "silent_until_next_feed": enabled}
        await self.store.save(data)
        self.async_set_updated_data(data)

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
            "deadline_override": None,
        }
        await self.store.save(data)
        self.async_set_updated_data(data)
        self._was_due, self._was_due_soon = self.schedule_state()
        self._fire(EVENT_LOCATION_CHANGED)
