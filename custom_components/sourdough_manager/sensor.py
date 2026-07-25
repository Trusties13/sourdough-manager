"""Sensors for Sourdough Manager."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorEntityDescription
from homeassistant.const import PERCENTAGE, UnitOfMass, UnitOfTemperature
from homeassistant.util import dt as dt_util

from .entity import StarterEntity
from .const import (
    CONF_PROGRAMME,
    CONF_REMINDER_DAYS,
    CONF_VESSEL_TARE,
    DEFAULT_PROGRAMME,
    DEFAULT_REMINDER_DAYS,
    DEFAULT_VESSEL_TARE,
)
from .models import (
    cycle_progress,
    cycle_status,
    feeding_instruction,
    next_feed_time,
    peak_times,
    programme_day,
    programme_phase,
)


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
    coordinator = entry.runtime_data
    entities = [StarterSensor(coordinator, description) for description in SENSORS]
    entities.extend(
        [
            StarterComputedSensor(coordinator, "total_weight_with_vessel", UnitOfMass.GRAMS, SensorDeviceClass.WEIGHT),
            StarterComputedSensor(coordinator, "suggested_discard", UnitOfMass.GRAMS, SensorDeviceClass.WEIGHT),
            StarterComputedSensor(coordinator, "suggested_water", UnitOfMass.GRAMS, SensorDeviceClass.WEIGHT),
            StarterComputedSensor(coordinator, "suggested_flour", UnitOfMass.GRAMS, SensorDeviceClass.WEIGHT),
            StarterComputedSensor(coordinator, "next_feed_due", None, SensorDeviceClass.TIMESTAMP),
            StarterComputedSensor(coordinator, "feeding_count"),
            StarterComputedSensor(coordinator, "programme_day"),
            StarterComputedSensor(coordinator, "programme_phase"),
            StarterComputedSensor(coordinator, "instructions"),
        ]
    )
    async_add_entities(entities)


class StarterSensor(StarterEntity, SensorEntity):
    entity_description: StarterSensorDescription

    def __init__(self, coordinator, description):
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def native_value(self):
        return self.entity_description.value_fn(self.coordinator.data)


class StarterComputedSensor(StarterEntity, SensorEntity):
    """A sensor calculated from settings and feed inputs."""

    _attr_has_entity_name = True

    def __init__(self, coordinator, key, unit=None, device_class=None):
        super().__init__(coordinator, key)
        self._attr_translation_key = key
        self._attr_native_unit_of_measurement = unit
        self._attr_device_class = device_class
        self.key = key

    @property
    def native_value(self):
        data = self.coordinator.data
        inputs = data["feed_inputs"]
        option = self.coordinator._option
        programme = option(CONF_PROGRAMME, DEFAULT_PROGRAMME)
        if self.key == "total_weight_with_vessel":
            return round(float(data.get("current_weight_g", 0)) + float(option(CONF_VESSEL_TARE, DEFAULT_VESSEL_TARE)), 1)
        if self.key == "suggested_discard":
            return round(max(0, float(data.get("current_weight_g", 0)) - float(inputs["starter_retained_g"])), 1)
        if self.key == "suggested_water":
            return inputs["water_added_g"]
        if self.key == "suggested_flour":
            return inputs["flour_added_g"]
        if self.key == "next_feed_due":
            return next_feed_time(data, programme, int(option(CONF_REMINDER_DAYS, DEFAULT_REMINDER_DAYS)))
        if self.key == "feeding_count":
            return data.get("feed_count", 0)
        if self.key == "programme_day":
            return programme_day(data) if programme == "new_starter" else None
        if self.key == "programme_phase":
            return programme_phase(data, programme)
        return feeding_instruction(
            data,
            programme,
            float(inputs["starter_retained_g"]),
            float(inputs["water_added_g"]),
            float(inputs["flour_added_g"]),
        )
