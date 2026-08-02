"""Sourdough Manager integration."""
from __future__ import annotations

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import entity_registry as er

from .const import DOMAIN, OBSOLETE_ENTITY_KEYS, PLATFORMS
from .coordinator import SourdoughCoordinator

SERVICE_SCHEMA = vol.Schema(
    {
        vol.Required("config_entry_id"): cv.string,
        vol.Optional("fed_at"): cv.datetime,
    }
)

SET_NEXT_DUE_SCHEMA = vol.Schema(
    {
        vol.Required("config_entry_id"): cv.string,
        vol.Required("due_at"): cv.datetime,
    }
)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Register the retrospective feed action."""

    async def record_feed(call: ServiceCall) -> None:
        entry = hass.config_entries.async_get_entry(call.data["config_entry_id"])
        if entry is None or entry.domain != DOMAIN or entry.runtime_data is None:
            raise ValueError("Unknown Sourdough Manager config entry")
        await entry.runtime_data.record_feed(call.data.get("fed_at"))

    hass.services.async_register(
        DOMAIN, "record_feed", record_feed, schema=SERVICE_SCHEMA
    )

    async def set_next_feed_due(call: ServiceCall) -> None:
        entry = hass.config_entries.async_get_entry(call.data["config_entry_id"])
        if entry is None or entry.domain != DOMAIN or entry.runtime_data is None:
            raise ValueError("Unknown Sourdough Manager config entry")
        await entry.runtime_data.set_next_feed_due(call.data["due_at"])

    hass.services.async_register(
        DOMAIN,
        "set_next_feed_due",
        set_next_feed_due,
        schema=SET_NEXT_DUE_SCHEMA,
    )
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up one starter."""
    coordinator = SourdoughCoordinator(hass, entry)
    await coordinator.async_load()
    entry.runtime_data = coordinator

    async def handle_notification_action(event) -> None:
        """Handle Companion App reminder actions for this starter."""
        action = event.data.get("action")
        if action == coordinator.feed_action:
            await coordinator.record_feed(protect_duplicate=True)
        elif action == coordinator.snooze_action:
            await coordinator.snooze()

    entry.async_on_unload(
        hass.bus.async_listen(
            "mobile_app_notification_action", handle_notification_action
        )
    )
    _remove_obsolete_entities(hass, entry)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_reload))
    return True


def _remove_obsolete_entities(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Remove entities retired by the focused tracker redesign."""
    registry = er.async_get(hass)
    for key in OBSOLETE_ENTITY_KEYS:
        if entity_id := registry.async_get_entity_id(
            "sensor", DOMAIN, f"{entry.entry_id}_{key}"
        ):
            registry.async_remove(entity_id)
        if entity_id := registry.async_get_entity_id(
            "button", DOMAIN, f"{entry.entry_id}_{key}"
        ):
            registry.async_remove(entity_id)
        if entity_id := registry.async_get_entity_id(
            "number", DOMAIN, f"{entry.entry_id}_{key}"
        ):
            registry.async_remove(entity_id)
        if entity_id := registry.async_get_entity_id(
            "select", DOMAIN, f"{entry.entry_id}_{key}"
        ):
            registry.async_remove(entity_id)
    for key in ("last_fed_time", "next_feed_deadline"):
        if entity_id := registry.async_get_entity_id(
            "datetime", DOMAIN, f"{entry.entry_id}_{key}"
        ):
            registry.async_remove(entity_id)
    if entity_id := registry.async_get_entity_id(
        "sensor", DOMAIN, f"{entry.entry_id}_missed_feed_count"
    ):
        registry.async_remove(entity_id)


async def _reload(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
