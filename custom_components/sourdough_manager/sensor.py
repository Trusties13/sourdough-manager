"""Timestamp sensors."""
from __future__ import annotations

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.helpers.entity import EntityCategory

from .const import (
    CONF_BENCH_INTERVAL,
    CONF_DUE_SOON,
    CONF_FRIDGE_INTERVAL,
    CONF_NOTIFICATION_TARGETS,
    DEFAULT_BENCH_INTERVAL,
    DEFAULT_DUE_SOON,
    DEFAULT_FRIDGE_INTERVAL,
)
from .entity import StarterEntity
from .models import human_duration, overdue_hours, parse_datetime


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
