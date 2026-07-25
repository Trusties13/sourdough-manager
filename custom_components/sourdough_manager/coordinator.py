"""Runtime coordinator."""
from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
from typing import Any
from uuid import uuid4

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from .const import (
    CONF_DEFAULT_TEMPERATURE,
    CONF_STARTER_HYDRATION,
    CONF_TEMPERATURE_ENTITY,
    DEFAULT_HYDRATION,
    DEFAULT_TEMPERATURE,
    DOMAIN,
)
from .models import feed_ratio, predict_peak, resulting_hydration
from .storage import StarterStore


class SourdoughCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Own state and atomic mutations for one starter."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(hass, logger=__import__("logging").getLogger(__name__), name=f"{DOMAIN}_{entry.entry_id}")
        self.entry = entry
        self.store = StarterStore(hass, entry.entry_id)

    async def async_load(self) -> None:
        self.async_set_updated_data(await self.store.load())

    def temperature(self) -> float:
        entity_id = self.entry.options.get(CONF_TEMPERATURE_ENTITY, self.entry.data.get(CONF_TEMPERATURE_ENTITY))
        if entity_id and (state := self.hass.states.get(entity_id)):
            try:
                value = float(state.state)
                if state.attributes.get("unit_of_measurement") == UnitOfTemperature.FAHRENHEIT:
                    return round((value - 32) * 5 / 9, 1)
                return value
            except (TypeError, ValueError):
                pass
        return float(self.entry.options.get(CONF_DEFAULT_TEMPERATURE, self.entry.data.get(CONF_DEFAULT_TEMPERATURE, DEFAULT_TEMPERATURE)))

    async def mutate(self, event_type: str, changes: dict[str, Any]) -> None:
        data = {**self.data, **changes}
        data["events"] = [*data.get("events", []), {"type": event_type, "timestamp": dt_util.utcnow().isoformat()}][-500:]
        await self.store.save(data)
        self.async_set_updated_data(data)
        self.hass.bus.async_fire(f"{DOMAIN}_{event_type}", {"config_entry_id": self.entry.entry_id})

    async def record_feed(self, call: dict[str, Any]) -> None:
        starter, water, flour = (float(call[key]) for key in ("starter_retained_g", "water_added_g", "flour_added_g"))
        fed_at: datetime = call.get("fed_at") or dt_util.utcnow()
        temperature = self.temperature()
        prediction = predict_peak(starter, flour, temperature, self.data.get("location") == "refrigerator", self.data.get("feed_history", []))
        hydration = resulting_hydration(starter, water, flour, float(self.entry.options.get(CONF_STARTER_HYDRATION, self.entry.data.get(CONF_STARTER_HYDRATION, DEFAULT_HYDRATION))))
        cycle = {
            "id": uuid4().hex,
            "fed_at": fed_at.isoformat(),
            "starter_g": starter, "water_g": water, "flour_g": flour,
            "total_g": starter + water + flour,
            "feed_ratio": feed_ratio(starter, water, flour),
            "hydration_percent": hydration,
            "flour_type": call.get("flour_type"),
            "temperature_c": temperature,
            "notes": call.get("notes", ""),
            "actual_peak_at": None,
            "prediction": asdict(prediction),
        }
        await self.mutate("feed_recorded", {"active_cycle": cycle, "current_weight_g": cycle["total_g"], "location": "bench", "warming": False})

    async def mark_peak(self) -> None:
        cycle = dict(self.data.get("active_cycle") or {})
        if not cycle:
            return
        now = dt_util.utcnow()
        fed_at = dt_util.parse_datetime(cycle["fed_at"])
        cycle["actual_peak_at"] = now.isoformat()
        cycle["actual_peak_hours"] = round((now - fed_at).total_seconds() / 3600, 3)
        history = [*self.data.get("feed_history", []), cycle][-250:]
        await self.mutate("peak_marked", {"active_cycle": cycle, "feed_history": history})

    async def adjust_weight(self, event: str, amount: float) -> None:
        await self.mutate(event, {"current_weight_g": max(0, float(self.data.get("current_weight_g", 0)) - amount)})
