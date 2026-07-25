"""Versioned persistent storage."""
from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import STORAGE_KEY_PREFIX, STORAGE_VERSION


class StarterStore:
    """Persist one starter's operational state."""

    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        self._store: Store[dict[str, Any]] = Store(hass, STORAGE_VERSION, f"{STORAGE_KEY_PREFIX}.{entry_id}")

    async def load(self) -> dict[str, Any]:
        """Load state."""
        return await self._store.async_load() or {
            "schema_version": STORAGE_VERSION,
            "location": "bench",
            "warming": False,
            "current_weight_g": 0.0,
            "active_cycle": None,
            "feed_history": [],
            "events": [],
        }

    async def save(self, data: dict[str, Any]) -> None:
        """Save state."""
        await self._store.async_save(data)
