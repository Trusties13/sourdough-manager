"""Due-state binary sensors."""
from homeassistant.components.binary_sensor import BinarySensorEntity

from .entity import StarterEntity


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up due-state sensors."""
    async_add_entities(
        [FeedDueSensor(entry.runtime_data), FeedDueSoonSensor(entry.runtime_data)]
    )


class FeedDueSensor(StarterEntity, BinarySensorEntity):
    """Whether the starter is due or overdue."""

    _attr_translation_key = "feed_due"

    def __init__(self, coordinator):
        super().__init__(coordinator, "feed_due")

    @property
    def is_on(self):
        return self.coordinator.schedule_state()[0]


class FeedDueSoonSensor(StarterEntity, BinarySensorEntity):
    """Whether the starter is approaching its deadline."""

    _attr_translation_key = "feed_due_soon"

    def __init__(self, coordinator):
        super().__init__(coordinator, "feed_due_soon")

    @property
    def is_on(self):
        return self.coordinator.schedule_state()[1]
