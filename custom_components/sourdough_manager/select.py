"""Storage location control."""
from homeassistant.components.select import SelectEntity

from .const import DELAY_OPTIONS, LOCATION_BENCH, LOCATIONS, SNOOZE_OPTIONS
from .entity import StarterEntity


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up starter selectors."""
    async_add_entities(
        [
            StorageLocationSelect(entry.runtime_data),
            SnoozeDurationSelect(entry.runtime_data),
            DelayDurationSelect(entry.runtime_data),
        ]
    )


class StorageLocationSelect(StarterEntity, SelectEntity):
    """Bench or refrigerator storage."""

    _attr_translation_key = "storage_location"
    _attr_options = list(LOCATIONS)

    def __init__(self, coordinator):
        super().__init__(coordinator, "storage_location")

    @property
    def current_option(self):
        return self.coordinator.data["location"]

    @property
    def icon(self) -> str:
        """Return an icon matching the current storage location."""
        if self.current_option == LOCATION_BENCH:
            return "mdi:table-furniture"
        return "mdi:fridge"

    async def async_select_option(self, option: str) -> None:
        await self.coordinator.set_location(option)


class SnoozeDurationSelect(StarterEntity, SelectEntity):
    """Select how long the Snooze action pauses reminders."""

    _attr_translation_key = "snooze_duration"
    _attr_options = list(SNOOZE_OPTIONS)

    def __init__(self, coordinator):
        super().__init__(coordinator, "snooze_duration")

    @property
    def current_option(self):
        return self.coordinator.data["snooze_hours"]

    async def async_select_option(self, option: str) -> None:
        await self.coordinator.set_snooze_duration(option)


class DelayDurationSelect(StarterEntity, SelectEntity):
    """Select the one-off next-feed delay."""

    _attr_translation_key = "delay_duration"
    _attr_options = list(DELAY_OPTIONS)

    def __init__(self, coordinator):
        super().__init__(coordinator, "delay_duration")

    @property
    def current_option(self):
        return self.coordinator.data.get("delay_option", "1")

    @property
    def available(self) -> bool:
        return super().available and self.coordinator.delay_available()

    async def async_select_option(self, option: str) -> None:
        await self.coordinator.set_delay_option(option)
