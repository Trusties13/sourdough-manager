"""Editable last-fed date."""
from __future__ import annotations

from datetime import date, datetime

from homeassistant.components.date import DateEntity
from homeassistant.helpers.entity import EntityCategory
from homeassistant.util import dt as dt_util

from .entity import StarterEntity
from .models import parse_datetime


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up the editable last-fed date."""
    async_add_entities([LastFedDate(entry.runtime_data)])


class LastFedDate(StarterEntity, DateEntity):
    """Allow the date of a late feeding entry to be corrected."""

    _attr_translation_key = "last_fed_date"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator):
        super().__init__(coordinator, "last_fed_date")

    @property
    def native_value(self) -> date | None:
        value = parse_datetime(self.coordinator.data.get("last_fed"))
        return dt_util.as_local(value).date() if value else None

    async def async_set_value(self, value: date) -> None:
        current = parse_datetime(self.coordinator.data.get("last_fed"))
        current_local = dt_util.as_local(current) if current else dt_util.now()
        whole_minute = current_local.time().replace(second=0, microsecond=0)
        combined = datetime.combine(value, whole_minute).replace(
            tzinfo=dt_util.get_default_time_zone()
        )
        await self.coordinator.record_feed(dt_util.as_utc(combined))
