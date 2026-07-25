"""Action buttons."""
from homeassistant.components.button import ButtonEntity, ButtonEntityDescription

from .entity import StarterEntity

BUTTONS = (
    ButtonEntityDescription(key="mark_peak", translation_key="mark_peak"),
    ButtonEntityDescription(key="refrigerate", translation_key="refrigerate"),
    ButtonEntityDescription(key="remove_from_fridge", translation_key="remove_from_fridge"),
    ButtonEntityDescription(key="cancel_cycle", translation_key="cancel_cycle"),
)


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities(StarterButton(entry.runtime_data, description) for description in BUTTONS)


class StarterButton(StarterEntity, ButtonEntity):
    def __init__(self, coordinator, description):
        super().__init__(coordinator, description.key)
        self.entity_description = description

    async def async_press(self):
        if self.entity_description.key == "mark_peak":
            await self.coordinator.mark_peak()
        elif self.entity_description.key == "refrigerate":
            await self.coordinator.mutate("refrigerated", {"location": "refrigerator", "warming": False})
        elif self.entity_description.key == "remove_from_fridge":
            await self.coordinator.mutate("removed_from_fridge", {"location": "bench", "warming": True})
        else:
            await self.coordinator.mutate("cycle_cancelled", {"active_cycle": None})
