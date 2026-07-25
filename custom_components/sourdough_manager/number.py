"""Dashboard-friendly feed inputs."""
from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberEntityDescription, NumberMode
from homeassistant.const import UnitOfMass

from .entity import StarterEntity

NUMBERS = (
    NumberEntityDescription(
        key="starter_retained_g",
        translation_key="starter_retained",
        native_min_value=0.1,
        native_max_value=5000,
        native_step=1,
        native_unit_of_measurement=UnitOfMass.GRAMS,
        mode=NumberMode.BOX,
    ),
    NumberEntityDescription(
        key="water_added_g",
        translation_key="water_added",
        native_min_value=0,
        native_max_value=5000,
        native_step=1,
        native_unit_of_measurement=UnitOfMass.GRAMS,
        mode=NumberMode.BOX,
    ),
    NumberEntityDescription(
        key="flour_added_g",
        translation_key="flour_added",
        native_min_value=0.1,
        native_max_value=5000,
        native_step=1,
        native_unit_of_measurement=UnitOfMass.GRAMS,
        mode=NumberMode.BOX,
    ),
)


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up feed input numbers."""
    async_add_entities(StarterFeedNumber(entry.runtime_data, description) for description in NUMBERS)


class StarterFeedNumber(StarterEntity, NumberEntity):
    """A persistent feed input."""

    def __init__(self, coordinator, description):
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def native_value(self):
        """Return the current input."""
        return self.coordinator.data["feed_inputs"][self.entity_description.key]

    async def async_set_native_value(self, value: float) -> None:
        """Update the input."""
        await self.coordinator.update_feed_input(self.entity_description.key, value)
