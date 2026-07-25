"""Sourdough Manager integration."""
from __future__ import annotations

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv

from .const import DOMAIN, PLATFORMS
from .coordinator import SourdoughCoordinator

SERVICE_SCHEMAS = {
    "record_feed": vol.Schema({
        vol.Required("config_entry_id"): cv.string,
        vol.Required("starter_retained_g"): vol.All(vol.Coerce(float), vol.Range(min=0.1)),
        vol.Required("water_added_g"): vol.All(vol.Coerce(float), vol.Range(min=0)),
        vol.Required("flour_added_g"): vol.All(vol.Coerce(float), vol.Range(min=0.1)),
        vol.Optional("flour_type", default="bread_flour"): cv.string,
        vol.Optional("fed_at"): cv.datetime,
        vol.Optional("notes", default=""): cv.string,
    }),
    "record_discard": vol.Schema({vol.Required("config_entry_id"): cv.string, vol.Required("amount_g"): vol.All(vol.Coerce(float), vol.Range(min=0.1))}),
    "record_use": vol.Schema({vol.Required("config_entry_id"): cv.string, vol.Required("amount_g"): vol.All(vol.Coerce(float), vol.Range(min=0.1))}),
}


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    async def handler(call: ServiceCall) -> None:
        entry = hass.config_entries.async_get_entry(call.data["config_entry_id"])
        if entry is None or entry.domain != DOMAIN or entry.runtime_data is None:
            raise ValueError("Unknown Sourdough Manager config entry")
        if call.service == "record_feed":
            await entry.runtime_data.record_feed(dict(call.data))
        else:
            await entry.runtime_data.adjust_weight(call.service, float(call.data["amount_g"]))

    for service, schema in SERVICE_SCHEMAS.items():
        hass.services.async_register(DOMAIN, service, handler, schema=schema)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    coordinator = SourdoughCoordinator(hass, entry)
    await coordinator.async_load()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_reload))
    return True


async def _reload(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
