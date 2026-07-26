"""Editable last-fed time."""
from __future__ import annotations

from datetime import datetime, time

from homeassistant.components.time import TimeEntity
from homeassistant.helpers.entity import EntityCategory
from homeassistant.util import dt as dt_util

from .entity import StarterEntity
from .models import parse_datetime


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up the editable last-fed time."""
    async_add_entities([LastFedTime(entry.runtime_data)])


class LastFedTime(StarterEntity, TimeEntity):
    """Allow the time of a late feeding entry to be corrected."""

    _attr_translation_key = "last_fed_clock"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator):
        super().__init__(coordinator, "last_fed_clock")

    @property
    def native_value(self) -> time | None:
        value = parse_datetime(self.coordinator.data.get("last_fed"))
        return dt_util.as_local(value).time() if value else None

    async def async_set_value(self, value: time) -> None:
        current = parse_datetime(self.coordinator.data.get("last_fed"))
        current_local = dt_util.as_local(current) if current else dt_util.now()
        combined = datetime.combine(current_local.date(), value).replace(
            tzinfo=dt_util.get_default_time_zone()
        )
        await self.coordinator.record_feed(dt_util.as_utc(combined))
