"""Config and options flows."""
from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_NAME
from homeassistant.helpers import selector

from .const import (
    CONF_DEFAULT_FLOUR,
    CONF_DEFAULT_TEMPERATURE,
    CONF_REMINDER_DAYS,
    CONF_STARTER_HYDRATION,
    CONF_STARTER_NAME,
    CONF_TEMPERATURE_ENTITY,
    DEFAULT_FLOUR,
    DEFAULT_HYDRATION,
    DEFAULT_REMINDER_DAYS,
    DEFAULT_TEMPERATURE,
    DOMAIN,
)


def _schema(defaults: dict, include_name: bool) -> vol.Schema:
    fields: dict = {}
    if include_name:
        fields[vol.Required(CONF_NAME, default=defaults.get(CONF_NAME, "Main Starter"))] = str
    fields.update({
        vol.Required(CONF_STARTER_HYDRATION, default=defaults.get(CONF_STARTER_HYDRATION, DEFAULT_HYDRATION)): vol.All(vol.Coerce(float), vol.Range(min=1, max=300)),
        vol.Required(CONF_DEFAULT_FLOUR, default=defaults.get(CONF_DEFAULT_FLOUR, DEFAULT_FLOUR)): selector.SelectSelector(selector.SelectSelectorConfig(options=["bread_flour", "plain_flour", "wholemeal_wheat", "rye", "spelt", "custom_blend", "other"], translation_key="flour")),
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
