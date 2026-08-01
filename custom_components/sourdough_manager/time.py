"""Editable last-fed time."""
from __future__ import annotations

from datetime import datetime, time

from homeassistant.components.time import TimeEntity
from homeassistant.helpers.entity import EntityCategory
from homeassistant.util import dt as dt_util

from .entity import StarterEntity
from .models import parse_datetime


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up editable feeding times."""
    async_add_entities(
        [
            LastFedTime(entry.runtime_data),
            NextFeedTime(entry.runtime_data),
        ]
    )


class LastFedTime(StarterEntity, TimeEntity):
    """Allow the time of a late feeding entry to be corrected."""

    _attr_translation_key = "last_fed_clock"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator):
        super().__init__(coordinator, "last_fed_clock")

    @property
    def native_value(self) -> time | None:
        value = parse_datetime(self.coordinator.data.get("last_fed"))
        if value is None:
            return None
        return dt_util.as_local(value).time().replace(second=0, microsecond=0)

    async def async_set_value(self, value: time) -> None:
        current = parse_datetime(self.coordinator.data.get("last_fed"))
        current_local = dt_util.as_local(current) if current else dt_util.now()
        whole_minute = value.replace(second=0, microsecond=0)
        combined = datetime.combine(current_local.date(), whole_minute).replace(
            tzinfo=dt_util.get_default_time_zone()
        )
        await self.coordinator.record_feed(dt_util.as_utc(combined))


class NextFeedTime(StarterEntity, TimeEntity):
    """Allow the next feeding time to be rescheduled."""

    _attr_translation_key = "next_feed_time"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator):
        super().__init__(coordinator, "next_feed_time")

    @property
    def native_value(self) -> time | None:
        due = self.coordinator.next_due()
        if due is None:
            return None
        return dt_util.as_local(due).time().replace(second=0, microsecond=0)

    @property
    def available(self) -> bool:
        return super().available and self.coordinator.next_due() is not None

    async def async_set_value(self, value: time) -> None:
        due = self.coordinator.next_due()
        if due is None:
            return
        local_due = dt_util.as_local(due)
        whole_minute = value.replace(second=0, microsecond=0)
        combined = datetime.combine(local_due.date(), whole_minute).replace(
            tzinfo=dt_util.get_default_time_zone()
        )
        await self.coordinator.set_next_feed_due(dt_util.as_utc(combined))
