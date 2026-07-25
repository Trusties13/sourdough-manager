"""Config and options flows."""
from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_NAME
from homeassistant.helpers import selector

from .const import (
    CONF_DEFAULT_FLOUR,
    CONF_DEFAULT_FLOUR_AMOUNT,
    CONF_DEFAULT_STARTER,
    CONF_DEFAULT_TEMPERATURE,
    CONF_DEFAULT_WATER,
    CONF_PROGRAMME,
    CONF_REMINDER_DAYS,
    CONF_STARTER_HYDRATION,
    CONF_STARTER_NAME,
    CONF_TEMPERATURE_ENTITY,
    CONF_VESSEL_TARE,
    DEFAULT_FLOUR,
    DEFAULT_FLOUR_AMOUNT,
    DEFAULT_HYDRATION,
    DEFAULT_PROGRAMME,
    DEFAULT_REMINDER_DAYS,
    DEFAULT_STARTER,
    DEFAULT_TEMPERATURE,
    DEFAULT_VESSEL_TARE,
    DEFAULT_WATER,
    DOMAIN,
    FLOUR_TYPES,
    PROGRAMMES,
)


def _schema(defaults: dict, include_name: bool) -> vol.Schema:
    fields: dict = {}
    if include_name:
        fields[vol.Required(CONF_NAME, default=defaults.get(CONF_NAME, "Main Starter"))] = str
    fields.update({
        vol.Required(CONF_STARTER_HYDRATION, default=defaults.get(CONF_STARTER_HYDRATION, DEFAULT_HYDRATION)): vol.All(vol.Coerce(float), vol.Range(min=1, max=300)),
        vol.Required(CONF_DEFAULT_FLOUR, default=defaults.get(CONF_DEFAULT_FLOUR, DEFAULT_FLOUR)): selector.SelectSelector(selector.SelectSelectorConfig(options=list(FLOUR_TYPES), translation_key="flour")),
        vol.Required(CONF_DEFAULT_STARTER, default=defaults.get(CONF_DEFAULT_STARTER, DEFAULT_STARTER)): vol.All(vol.Coerce(float), vol.Range(min=0.1, max=5000)),
        vol.Required(CONF_DEFAULT_WATER, default=defaults.get(CONF_DEFAULT_WATER, DEFAULT_WATER)): vol.All(vol.Coerce(float), vol.Range(min=0, max=5000)),
        vol.Required(CONF_DEFAULT_FLOUR_AMOUNT, default=defaults.get(CONF_DEFAULT_FLOUR_AMOUNT, DEFAULT_FLOUR_AMOUNT)): vol.All(vol.Coerce(float), vol.Range(min=0.1, max=5000)),
        vol.Required(CONF_VESSEL_TARE, default=defaults.get(CONF_VESSEL_TARE, DEFAULT_VESSEL_TARE)): vol.All(vol.Coerce(float), vol.Range(min=0, max=5000)),
        vol.Required(CONF_PROGRAMME, default=defaults.get(CONF_PROGRAMME, DEFAULT_PROGRAMME)): selector.SelectSelector(selector.SelectSelectorConfig(options=list(PROGRAMMES), translation_key="programme")),
        vol.Optional(CONF_TEMPERATURE_ENTITY, default=defaults.get(CONF_TEMPERATURE_ENTITY)): selector.EntitySelector(selector.EntitySelectorConfig(domain="sensor", device_class="temperature")),
        vol.Required(CONF_DEFAULT_TEMPERATURE, default=defaults.get(CONF_DEFAULT_TEMPERATURE, DEFAULT_TEMPERATURE)): vol.All(vol.Coerce(float), vol.Range(min=0, max=40)),
        vol.Required(CONF_REMINDER_DAYS, default=defaults.get(CONF_REMINDER_DAYS, DEFAULT_REMINDER_DAYS)): vol.All(vol.Coerce(int), vol.Range(min=1, max=90)),
    })
    return vol.Schema(fields)


class SourdoughConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Configure a starter."""
    VERSION = 1

    async def async_step_user(self, user_input=None):
        if user_input is None:
            return self.async_show_form(step_id="user", data_schema=_schema({}, True))
        name = user_input.pop(CONF_NAME)
        return self.async_create_entry(title=name, data={CONF_STARTER_NAME: name, **user_input})

    @staticmethod
    def async_get_options_flow(config_entry):
        return SourdoughOptionsFlow()


class SourdoughOptionsFlow(config_entries.OptionsFlow):
    """Edit starter settings."""

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(data=user_input)
        defaults = {**self.config_entry.data, **self.config_entry.options}
        return self.async_show_form(step_id="init", data_schema=_schema(defaults, False))
