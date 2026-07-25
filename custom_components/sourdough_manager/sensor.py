"""Sensors for Sourdough Manager."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorEntityDescription
from homeassistant.const import PERCENTAGE, UnitOfMass, UnitOfTemperature
from homeassistant.util import dt as dt_util

from .entity import StarterEntity
from .models import cycle_progress, cycle_status, peak_times


@dataclass(frozen=True, kw_only=True)
class StarterSensorDescription(SensorEntityDescription):
    value_fn: Callable


SENSORS = (
    StarterSensorDescription(key="status", translation_key="status", value_fn=lambda d: cycle_status(d)),
    StarterSensorDescription(key="last_fed", translation_key="last_fed", device_class=SensorDeviceClass.TIMESTAMP, value_fn=lambda d: dt_util.parse_datetime(d["active_cycle"]["fed_at"]) if d.get("active_cycle") else None),
    StarterSensorDescription(key="expected_peak", translation_key="expected_peak", device_class=SensorDeviceClass.TIMESTAMP, value_fn=lambda d: peak_times(d["active_cycle"])[0] if d.get("active_cycle") else None),
    StarterSensorDescription(key="peak_window_start", translation_key="peak_window_start", device_class=SensorDeviceClass.TIMESTAMP, entity_registry_enabled_default=False, value_fn=lambda d: peak_times(d["active_cycle"])[1] if d.get("active_cycle") else None),
    StarterSensorDescription(key="peak_window_end", translation_key="peak_window_end", device_class=SensorDeviceClass.TIMESTAMP, entity_registry_enabled_default=False, value_fn=lambda d: peak_times(d["active_cycle"])[2] if d.get("active_cycle") else None),
    StarterSensorDescription(key="current_weight", translation_key="current_weight", native_unit_of_measurement=UnitOfMass.GRAMS, device_class=SensorDeviceClass.WEIGHT, value_fn=lambda d: d.get("current_weight_g")),
    StarterSensorDescription(key="feed_ratio", translation_key="feed_ratio", value_fn=lambda d: d["active_cycle"]["feed_ratio"] if d.get("active_cycle") else None),
    StarterSensorDescription(key="hydration", translation_key="hydration", native_unit_of_measurement=PERCENTAGE, value_fn=lambda d: d["active_cycle"]["hydration_percent"] if d.get("active_cycle") else None),
    StarterSensorDescription(key="cycle_progress", translation_key="cycle_progress", native_unit_of_measurement=PERCENTAGE, value_fn=cycle_progress),
    StarterSensorDescription(key="prediction_confidence", translation_key="prediction_confidence", value_fn=lambda d: d["active_cycle"]["prediction"]["confidence"] if d.get("active_cycle") else None),
    StarterSensorDescription(key="average_temperature", translation_key="average_temperature", native_unit_of_measurement=UnitOfTemperature.CELSIUS, device_class=SensorDeviceClass.TEMPERATURE, value_fn=lambda d: d["active_cycle"]["temperature_c"] if d.get("active_cycle") else None),
    StarterSensorDescription(key="last_peak_duration", translation_key="last_peak_duration", native_unit_of_measurement="h", device_class=SensorDeviceClass.DURATION, value_fn=lambda d: d["feed_history"][-1].get("actual_peak_hours") if d.get("feed_history") else None),
)


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities(StarterSensor(entry.runtime_data, description) for description in SENSORS)


class StarterSensor(StarterEntity, SensorEntity):
    entity_description: StarterSensorDescription

    def __init__(self, coordinator, description):
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def native_value(self):
        return self.entity_description.value_fn(self.coordinator.data)
