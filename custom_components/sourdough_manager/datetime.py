"""Editable one-off feeding deadline."""
from __future__ import annotations

from datetime import datetime

from homeassistant.components.datetime import DateTimeEntity
from homeassistant.exceptions import HomeAssistantError

from .entity import StarterEntity


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up editable deadline entities."""
    async_add_entities([NextFeedDeadlineEntity(entry.runtime_data)])


class NextFeedDeadlineEntity(StarterEntity, DateTimeEntity):
    """Allow a one-off replacement for the next feeding deadline."""

    _attr_translation_key = "next_feed_deadline"

    def __init__(self, coordinator):
        super().__init__(coordinator, "next_feed_deadline")

    @property
    def native_value(self):
        return self.coordinator.next_due()

    @property
    def available(self) -> bool:
        return super().available and self.coordinator.delay_available()

    async def async_set_value(self, value: datetime) -> None:
        if not self.coordinator.delay_available():
            raise HomeAssistantError(
                "The next feeding can only be changed on its due date or while overdue"
            )
        await self.coordinator.set_next_feed_due(value)
