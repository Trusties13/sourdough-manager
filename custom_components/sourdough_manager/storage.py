"""Versioned persistent storage."""
from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import SCHEMA_VERSION, STORAGE_KEY_PREFIX, STORAGE_VERSION
from .models import migrate_storage


class StarterStore:
    """Persist one starter's focused state."""

    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        self._store: Store[dict[str, Any]] = Store(
            hass, STORAGE_VERSION, f"{STORAGE_KEY_PREFIX}.{entry_id}"
        )

    async def load(self, default_location: str, initial_last_fed: str | None) -> dict[str, Any]:
        """Load and migrate state."""
        stored = await self._store.async_load()
        if stored is None:
            data = {
                "schema_version": SCHEMA_VERSION,
                "last_fed": initial_last_fed,
                "location": default_location,
                "location_changed_at": None,
                "last_reminder_for": None,
                "last_overdue_reminder_at": None,
                "last_reminder_sent_at": None,
                "snoozed_until": None,
                "snooze_hours": "1",
                "last_audio_reminder_at": None,
            }
        else:
            data = migrate_storage(stored, default_location)
        if stored != data:
            await self.save(data)
        return data

    async def save(self, data: dict[str, Any]) -> None:
        """Save state."""
        await self._store.async_save(data)
