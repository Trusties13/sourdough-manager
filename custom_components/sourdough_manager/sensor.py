"""Timestamp sensors."""
from __future__ import annotations

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.helpers.entity import EntityCategory

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
    CONF_LIGHT_COLOR,
    CONF_LIGHT_FLASH_COUNT,
    CONF_LIGHT_GAP_SECONDS,
    CONF_LIGHT_PULSE_SECONDS,
    CONF_LIGHT_TARGETS,
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
    DEFAULT_LIGHT_FLASH_COUNT,
    DEFAULT_LIGHT_GAP_SECONDS,
    DEFAULT_LIGHT_PULSE_SECONDS,
    DEFAULT_OVERDUE_INTERVAL,
    DEFAULT_QUIET_END,
    DEFAULT_QUIET_START,
)
from .entity import StarterEntity
from .models import human_clock_range, human_duration, overdue_hours, parse_datetime


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up timestamp sensors."""
    async_add_entities(
        [
            LastFedSensor(entry.runtime_data),
            NextFeedDueSensor(entry.runtime_data),
            DurationSettingSensor(
                entry.runtime_data,
                "bench_feed_frequency",
                CONF_BENCH_INTERVAL,
                DEFAULT_BENCH_INTERVAL,
            ),
            DurationSettingSensor(
                entry.runtime_data,
                "fridge_feed_frequency",
                CONF_FRIDGE_INTERVAL,
                DEFAULT_FRIDGE_INTERVAL,
            ),
            DurationSettingSensor(
                entry.runtime_data,
                "reminder_lead_time",
                CONF_DUE_SOON,
                DEFAULT_DUE_SOON,
            ),
            NotificationTargetsSensor(entry.runtime_data),
            OverdueIntervalSensor(entry.runtime_data),
            QuietHoursSensor(entry.runtime_data),
            FeedConfirmationSensor(entry.runtime_data),
            LastReminderSentSensor(entry.runtime_data),
            AudioStatusSensor(entry.runtime_data),
            AudioTtsSensor(entry.runtime_data),
            AudioTargetsSensor(entry.runtime_data),
            DurationSettingSensor(
                entry.runtime_data,
                "audio_lead_time",
                CONF_AUDIO_LEAD_TIME,
                DEFAULT_AUDIO_LEAD_TIME,
            ),
            AudioIntervalSensor(entry.runtime_data),
            AudioVolumeSensor(entry.runtime_data),
            LastAudioReminderSensor(entry.runtime_data),
            LightTargetsSensor(entry.runtime_data),
            LightColorSensor(entry.runtime_data),
            LightTimingSensor(entry.runtime_data),
            LastLightReminderSensor(entry.runtime_data),
        ]
    )


class LastFedSensor(StarterEntity, SensorEntity):
    """Last recorded feeding."""

    _attr_translation_key = "last_fed"
    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(self, coordinator):
        super().__init__(coordinator, "last_fed")

    @property
    def native_value(self):
        return parse_datetime(self.coordinator.data.get("last_fed"))


class NextFeedDueSensor(StarterEntity, SensorEntity):
    """Next feeding deadline."""

    _attr_translation_key = "next_feed_due"
    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(self, coordinator):
        super().__init__(coordinator, "next_feed_due")

    @property
    def native_value(self):
        return self.coordinator.next_due()

    @property
    def extra_state_attributes(self):
        return {
            "overdue_hours": overdue_hours(self.coordinator.next_due()),
            "location": self.coordinator.data["location"],
            "location_changed_at": self.coordinator.data.get("location_changed_at"),
        }


class DurationSettingSensor(StarterEntity, SensorEntity):
    """A human-friendly configured duration."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator, key, option_key, default):
        super().__init__(coordinator, key)
        self._attr_translation_key = key
        self._option_key = option_key
        self._default = default

    @property
    def native_value(self):
        return human_duration(float(self.coordinator.option(self._option_key, self._default)))

    @property
    def extra_state_attributes(self):
        return {
            "hours": float(self.coordinator.option(self._option_key, self._default))
        }


class NotificationTargetsSensor(StarterEntity, SensorEntity):
    """Configured reminder recipients."""

    _attr_translation_key = "notification_targets"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator):
        super().__init__(coordinator, "notification_targets")

    @property
    def native_value(self):
        targets = self.coordinator.option(CONF_NOTIFICATION_TARGETS, [])
        if isinstance(targets, str):
            targets = [targets]
        if not targets:
            return "Not configured"
        names = [
            self.hass.states.get(entity_id).name
            if self.hass.states.get(entity_id)
            else entity_id
            for entity_id in targets
        ]
        return ", ".join(names)[:255]

    @property
    def extra_state_attributes(self):
        targets = self.coordinator.option(CONF_NOTIFICATION_TARGETS, [])
        return {"entity_ids": [targets] if isinstance(targets, str) else targets}


class OverdueIntervalSensor(DurationSettingSensor):
    """Configured repeat interval for overdue reminders."""

    def __init__(self, coordinator):
        StarterEntity.__init__(self, coordinator, "overdue_reminder_interval")
        self._attr_translation_key = "overdue_reminder_interval"

    @property
    def native_value(self):
        minutes = float(
            self.coordinator.option(
                CONF_OVERDUE_INTERVAL, DEFAULT_OVERDUE_INTERVAL
            )
        )
        return human_duration(minutes / 60)

    @property
    def extra_state_attributes(self):
        return {
            "minutes": float(
                self.coordinator.option(
                    CONF_OVERDUE_INTERVAL, DEFAULT_OVERDUE_INTERVAL
                )
            )
        }


class QuietHoursSensor(StarterEntity, SensorEntity):
    """Configured notification quiet period."""

    _attr_translation_key = "quiet_hours"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator):
        super().__init__(coordinator, "quiet_hours")

    @property
    def native_value(self):
        if not bool(self.coordinator.option(CONF_QUIET_HOURS_ENABLED, False)):
            return "Disabled"
        return human_clock_range(
            self.coordinator.option(CONF_QUIET_START, DEFAULT_QUIET_START),
            self.coordinator.option(CONF_QUIET_END, DEFAULT_QUIET_END),
        )


class FeedConfirmationSensor(StarterEntity, SensorEntity):
    """Whether feed confirmation notifications are enabled."""

    _attr_translation_key = "feed_confirmation"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator):
        super().__init__(coordinator, "feed_confirmation")

    @property
    def native_value(self):
        return (
            "Enabled"
            if bool(self.coordinator.option(CONF_CONFIRM_FEED, False))
            else "Disabled"
        )


class LastReminderSentSensor(StarterEntity, SensorEntity):
    """Timestamp of the most recent feeding reminder."""

    _attr_translation_key = "last_reminder_sent"
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator):
        super().__init__(coordinator, "last_reminder_sent")

    @property
    def native_value(self):
        return parse_datetime(self.coordinator.data.get("last_reminder_sent_at"))


class AudioStatusSensor(StarterEntity, SensorEntity):
    """Whether spoken reminders are enabled."""

    _attr_translation_key = "audio_reminders"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator):
        super().__init__(coordinator, "audio_reminders")

    @property
    def native_value(self):
        return (
            "Enabled"
            if bool(self.coordinator.option(CONF_AUDIO_ENABLED, False))
            else "Disabled"
        )


class AudioTtsSensor(StarterEntity, SensorEntity):
    """Configured text-to-speech provider."""

    _attr_translation_key = "audio_tts_provider"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator):
        super().__init__(coordinator, "audio_tts_provider")

    @property
    def native_value(self):
        entity_id = self.coordinator.option(CONF_AUDIO_TTS_ENTITY, None)
        if not entity_id:
            return "Not configured"
        state = self.hass.states.get(entity_id)
        return state.name if state else entity_id


class AudioTargetsSensor(StarterEntity, SensorEntity):
    """Configured spoken reminder targets."""

    _attr_translation_key = "audio_targets"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator):
        super().__init__(coordinator, "audio_targets")

    @property
    def native_value(self):
        targets = self.coordinator.option(CONF_AUDIO_TARGETS, [])
        if isinstance(targets, str):
            targets = [targets]
        if not targets:
            return "Not configured"
        names = [
            self.hass.states.get(entity_id).name
            if self.hass.states.get(entity_id)
            else entity_id
            for entity_id in targets
        ]
        return ", ".join(names)[:255]


class AudioIntervalSensor(OverdueIntervalSensor):
    """Configured repeat interval for spoken reminders."""

    def __init__(self, coordinator):
        StarterEntity.__init__(self, coordinator, "audio_reminder_interval")
        self._attr_translation_key = "audio_reminder_interval"

    @property
    def native_value(self):
        minutes = float(
            self.coordinator.option(CONF_AUDIO_INTERVAL, DEFAULT_AUDIO_INTERVAL)
        )
        return human_duration(minutes / 60)

    @property
    def extra_state_attributes(self):
        return {
            "minutes": float(
                self.coordinator.option(
                    CONF_AUDIO_INTERVAL, DEFAULT_AUDIO_INTERVAL
                )
            )
        }


class AudioVolumeSensor(StarterEntity, SensorEntity):
    """Configured spoken reminder volume."""

    _attr_translation_key = "audio_volume"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator):
        super().__init__(coordinator, "audio_volume")

    @property
    def native_value(self):
        volume = float(
            self.coordinator.option(
                CONF_AUDIO_VOLUME, DEFAULT_AUDIO_VOLUME
            )
        )
        return f"{volume:g}%"


class LastAudioReminderSensor(StarterEntity, SensorEntity):
    """Timestamp of the most recent spoken reminder."""

    _attr_translation_key = "last_audio_reminder"
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator):
        super().__init__(coordinator, "last_audio_reminder")

    @property
    def native_value(self):
        return parse_datetime(
            self.coordinator.data.get("last_audio_reminder_at")
        )


class LightTargetsSensor(StarterEntity, SensorEntity):
    """Configured visual reminder targets."""

    _attr_translation_key = "light_targets"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator):
        super().__init__(coordinator, "light_targets")

    @property
    def native_value(self):
        targets = self.coordinator.option(CONF_LIGHT_TARGETS, [])
        if isinstance(targets, str):
            targets = [targets]
        if not targets:
            return "Not configured"
        names = [
            self.hass.states.get(entity_id).name
            if self.hass.states.get(entity_id)
            else entity_id
            for entity_id in targets
        ]
        return ", ".join(names)[:255]


class LastLightReminderSensor(StarterEntity, SensorEntity):
    """Timestamp of the most recent light reminder."""

    _attr_translation_key = "last_light_reminder"
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator):
        super().__init__(coordinator, "last_light_reminder")

    @property
    def native_value(self):
        return parse_datetime(
            self.coordinator.data.get("last_light_reminder_at")
        )


class LightColorSensor(StarterEntity, SensorEntity):
    """Configured visual reminder colour."""

    _attr_translation_key = "light_color"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator):
        super().__init__(coordinator, "light_color")

    @property
    def native_value(self):
        red, green, blue = self.coordinator.option(
            CONF_LIGHT_COLOR, DEFAULT_LIGHT_COLOR
        )
        return f"RGB {red}, {green}, {blue}"


class LightTimingSensor(StarterEntity, SensorEntity):
    """Configured light reminder timing."""

    _attr_translation_key = "light_timing"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator):
        super().__init__(coordinator, "light_timing")

    @property
    def native_value(self):
        count = int(
            self.coordinator.option(
                CONF_LIGHT_FLASH_COUNT, DEFAULT_LIGHT_FLASH_COUNT
            )
        )
        pulse = float(
            self.coordinator.option(
                CONF_LIGHT_PULSE_SECONDS, DEFAULT_LIGHT_PULSE_SECONDS
            )
        )
        gap = float(
            self.coordinator.option(
                CONF_LIGHT_GAP_SECONDS, DEFAULT_LIGHT_GAP_SECONDS
            )
        )
        return f"{count} × {pulse:g}s, {gap:g}s gap"
