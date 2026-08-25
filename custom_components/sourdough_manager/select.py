"""Starter selectors."""
from homeassistant.components.select import SelectEntity
from homeassistant.util import dt as dt_util

from .const import DELAY_OPTIONS, LOCATION_BENCH, LOCATIONS, SNOOZE_OPTIONS
from .entity import StarterEntity
from .models import parse_datetime


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up starter selectors."""
    async_add_entities(
        [
            StorageLocationSelect(entry.runtime_data),
            SnoozeDurationSelect(entry.runtime_data),
            DelayDurationSelect(entry.runtime_data),
            FeedToEditSelect(entry.runtime_data),
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


class FeedToEditSelect(StarterEntity, SelectEntity):
    """Select a feed-history record for correction or deletion."""

    _attr_translation_key = "feed_to_edit"

    def __init__(self, coordinator):
        super().__init__(coordinator, "feed_to_edit")

    def _option_map(self) -> dict[str, str]:
        """Return user-facing labels mapped to stable feed IDs."""
        options: dict[str, str] = {}
        history = reversed(self.coordinator.data.get("feed_history", []))
        for item in history:
            fed_at = parse_datetime(item.get("fed_at"))
            if fed_at is None or not item.get("id"):
                continue
            local = dt_util.as_local(fed_at)
            location = (
                "Fridge" if item.get("location") == "refrigerator" else "Bench"
            )
            label = f"{local:%a, %d %b %Y at %I:%M %p} — {location}"
            if label in options:
                label = f"{label} · {str(item['id'])[:6]}"
            options[label] = item["id"]
        return options

    @property
    def options(self) -> list[str]:
        return list(self._option_map())

    @property
    def current_option(self) -> str | None:
        selected_id = self.coordinator.data.get("selected_feed_id")
        return next(
            (
                label
                for label, feed_id in self._option_map().items()
                if feed_id == selected_id
            ),
            None,
        )

    @property
    def available(self) -> bool:
        return super().available and bool(self.options)

    async def async_select_option(self, option: str) -> None:
        selected_id = self._option_map().get(option)
        if selected_id is not None:
            await self.coordinator.select_feed(selected_id)
