"""Editable last-fed date."""
from __future__ import annotations

from datetime import date, datetime

from homeassistant.components.date import DateEntity
from homeassistant.helpers.entity import EntityCategory
from homeassistant.util import dt as dt_util

from .entity import StarterEntity
from .models import parse_datetime


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up editable feeding dates."""
    async_add_entities(
        [
            LastFedDate(entry.runtime_data),
            NextFeedDate(entry.runtime_data),
        ]
    )


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


class NextFeedDate(StarterEntity, DateEntity):
    """Allow the next feeding date to be rescheduled."""

    _attr_translation_key = "next_feed_date"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator):
        super().__init__(coordinator, "next_feed_date")

    @property
    def native_value(self) -> date | None:
        due = self.coordinator.next_due()
        return dt_util.as_local(due).date() if due else None

    @property
    def available(self) -> bool:
        return super().available and self.coordinator.next_due() is not None

    async def async_set_value(self, value: date) -> None:
        due = self.coordinator.next_due()
        if due is None:
            return
        local_due = dt_util.as_local(due)
        whole_minute = local_due.time().replace(second=0, microsecond=0)
        combined = datetime.combine(value, whole_minute).replace(
            tzinfo=dt_util.get_default_time_zone()
        )
        await self.coordinator.set_next_feed_due(dt_util.as_utc(combined))
