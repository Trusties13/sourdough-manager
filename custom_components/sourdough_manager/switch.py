"""Reminder master switch."""
from homeassistant.components.switch import SwitchEntity
from homeassistant.helpers.entity import EntityCategory

from .entity import StarterEntity


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up reminder controls."""
    async_add_entities([ReminderMasterSwitch(entry.runtime_data)])


class ReminderMasterSwitch(StarterEntity, SwitchEntity):
    """Enable or disable all scheduled reminders."""

    _attr_translation_key = "reminders"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator):
        super().__init__(coordinator, "reminders")

    @property
    def is_on(self) -> bool:
        """Return whether scheduled reminders are enabled."""
        return bool(self.coordinator.data.get("reminders_enabled", True))

    async def async_turn_on(self, **kwargs) -> None:
        """Enable scheduled reminders."""
        await self.coordinator.set_reminders_enabled(True)

    async def async_turn_off(self, **kwargs) -> None:
        """Disable scheduled reminders."""
        await self.coordinator.set_reminders_enabled(False)
