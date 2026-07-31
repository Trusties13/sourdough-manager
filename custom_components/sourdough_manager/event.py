"""Native starter event entity."""
from homeassistant.components.event import EventEntity

from .const import EVENT_TYPES
from .entity import StarterEntity


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up the starter event stream."""
    async_add_entities([StarterEventEntity(entry.runtime_data)])


class StarterEventEntity(StarterEntity, EventEntity):
    """Expose feeding lifecycle events to the automation editor."""

    _attr_translation_key = "starter_event"
    _attr_event_types = list(EVENT_TYPES)

    def __init__(self, coordinator):
        super().__init__(coordinator, "starter_event")

    async def async_added_to_hass(self) -> None:
        """Subscribe to coordinator events."""
        await super().async_added_to_hass()
        self.async_on_remove(
            self.coordinator.add_event_listener(self._handle_event)
        )

    def _handle_event(self, event_type, event_data) -> None:
        """Publish a native Home Assistant event."""
        self._trigger_event(event_type, event_data)
        self.async_write_ha_state()
