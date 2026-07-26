"""Timestamp sensors."""
from __future__ import annotations

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity

from .entity import StarterEntity
from .models import overdue_hours, parse_datetime


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up timestamp sensors."""
    async_add_entities(
        [LastFedSensor(entry.runtime_data), NextFeedDueSensor(entry.runtime_data)]
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
