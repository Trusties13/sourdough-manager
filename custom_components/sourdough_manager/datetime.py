"""Editable last-fed date and time."""
from __future__ import annotations

from datetime import datetime

from homeassistant.components.datetime import DateTimeEntity

from .entity import StarterEntity
from .models import parse_datetime


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up the editable last-fed time."""
    async_add_entities([LastFedDateTime(entry.runtime_data)])


class LastFedDateTime(StarterEntity, DateTimeEntity):
    """Allow a late feeding entry to be backdated."""

    _attr_translation_key = "last_fed_time"

    def __init__(self, coordinator):
        super().__init__(coordinator, "last_fed_time")

    @property
    def native_value(self) -> datetime | None:
        return parse_datetime(self.coordinator.data.get("last_fed"))

    async def async_set_value(self, value: datetime) -> None:
        await self.coordinator.record_feed(value)
