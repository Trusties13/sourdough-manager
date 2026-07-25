"""Dashboard-friendly feed selections."""
from __future__ import annotations

from homeassistant.components.select import SelectEntity, SelectEntityDescription

from .const import FLOUR_TYPES
from .entity import StarterEntity


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up feed selectors."""
    async_add_entities(
        [
            StarterFeedSelect(
                entry.runtime_data,
                SelectEntityDescription(
                    key="flour_type",
                    translation_key="feed_flour_type",
                    options=list(FLOUR_TYPES),
                ),
            )
        ]
    )


class StarterFeedSelect(StarterEntity, SelectEntity):
    """A persistent feed selection."""

    def __init__(self, coordinator, description):
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def current_option(self):
        """Return the selected option."""
        return self.coordinator.data["feed_inputs"][self.entity_description.key]

    async def async_select_option(self, option: str) -> None:
        """Update the selected option."""
        await self.coordinator.update_feed_input(self.entity_description.key, option)
