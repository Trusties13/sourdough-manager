"""Reminder master switch."""
from homeassistant.components.switch import SwitchEntity
from homeassistant.helpers.entity import EntityCategory

from .entity import StarterEntity


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up reminder controls."""
    async_add_entities(
        [
            ReminderMasterSwitch(entry.runtime_data),
            ReminderChannelSwitch(entry.runtime_data, "push"),
            ReminderChannelSwitch(entry.runtime_data, "audio"),
            ReminderChannelSwitch(entry.runtime_data, "light"),
            SilentUntilFeedSwitch(entry.runtime_data),
        ]
    )


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


class ReminderChannelSwitch(StarterEntity, SwitchEntity):
    """Enable one scheduled reminder channel."""

    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator, channel: str):
        super().__init__(coordinator, f"{channel}_reminders")
        self.channel = channel
        self._attr_translation_key = f"{channel}_reminders"

    @property
    def is_on(self) -> bool:
        """Return whether this channel is enabled."""
        return self.coordinator.channel_enabled(self.channel)

    async def async_turn_on(self, **kwargs) -> None:
        """Enable this reminder channel."""
        await self.coordinator.set_channel_enabled(self.channel, True)

    async def async_turn_off(self, **kwargs) -> None:
        """Disable this reminder channel."""
        await self.coordinator.set_channel_enabled(self.channel, False)


class SilentUntilFeedSwitch(StarterEntity, SwitchEntity):
    """Mute audio and light reminders until the next feed."""

    _attr_translation_key = "silent_until_next_feed"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator):
        super().__init__(coordinator, "silent_until_next_feed")

    @property
    def is_on(self) -> bool:
        """Return whether disruptive reminders are muted for this cycle."""
        return bool(self.coordinator.data.get("silent_until_next_feed", False))

    async def async_turn_on(self, **kwargs) -> None:
        await self.coordinator.set_silent_until_next_feed(True)

    async def async_turn_off(self, **kwargs) -> None:
        await self.coordinator.set_silent_until_next_feed(False)
