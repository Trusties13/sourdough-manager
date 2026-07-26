"""Storage location control."""
from homeassistant.components.select import SelectEntity

from .const import LOCATIONS
from .entity import StarterEntity


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up the storage location selector."""
    async_add_entities([StorageLocationSelect(entry.runtime_data)])


class StorageLocationSelect(StarterEntity, SelectEntity):
    """Bench or refrigerator storage."""

    _attr_translation_key = "storage_location"
    _attr_options = list(LOCATIONS)

    def __init__(self, coordinator):
        super().__init__(coordinator, "storage_location")

    @property
    def current_option(self):
        return self.coordinator.data["location"]

    async def async_select_option(self, option: str) -> None:
        await self.coordinator.set_location(option)
