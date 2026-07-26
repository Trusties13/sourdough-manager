"""Feeding action button."""
from homeassistant.components.button import ButtonEntity

from .entity import StarterEntity


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up feeding action buttons."""
    async_add_entities(
        [
            FedNowButton(entry.runtime_data),
            SnoozeButton(entry.runtime_data),
            TestPushReminderButton(entry.runtime_data),
            TestAudioReminderButton(entry.runtime_data),
        ]
    )


class FedNowButton(StarterEntity, ButtonEntity):
    """Record a feeding at the current time."""

    _attr_translation_key = "fed_now"

    def __init__(self, coordinator):
        super().__init__(coordinator, "fed_now")

    async def async_press(self):
        await self.coordinator.record_feed(protect_duplicate=True)


class SnoozeButton(StarterEntity, ButtonEntity):
    """Pause reminder notifications for the selected duration."""

    _attr_translation_key = "snooze"

    def __init__(self, coordinator):
        super().__init__(coordinator, "snooze")

    async def async_press(self):
        await self.coordinator.snooze()


class TestPushReminderButton(StarterEntity, ButtonEntity):
    """Send a test push reminder to the configured targets."""

    _attr_translation_key = "test_push_reminder"

    def __init__(self, coordinator):
        super().__init__(coordinator, "test_push_reminder")

    async def async_press(self):
        await self.coordinator.test_push_reminder()


class TestAudioReminderButton(StarterEntity, ButtonEntity):
    """Send a test audio reminder to the configured targets."""

    _attr_translation_key = "test_audio_reminder"

    def __init__(self, coordinator):
        super().__init__(coordinator, "test_audio_reminder")

    async def async_press(self):
        await self.coordinator.test_audio_reminder()
