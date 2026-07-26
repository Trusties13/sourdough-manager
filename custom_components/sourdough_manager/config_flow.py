"""Config and options flows."""
from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_NAME
from homeassistant.helpers import selector

from .const import (
    CONF_BENCH_INTERVAL,
    CONF_DUE_SOON,
    CONF_FRIDGE_INTERVAL,
    CONF_LAST_FED,
    CONF_LOCATION,
    CONF_STARTER_NAME,
    DEFAULT_BENCH_INTERVAL,
    DEFAULT_DUE_SOON,
    DEFAULT_FRIDGE_INTERVAL,
    DOMAIN,
    LOCATIONS,
)


def _interval(value: float) -> float:
    return vol.All(vol.Coerce(float), vol.Range(min=1, max=2160))(value)


def _schema(defaults: dict, include_identity: bool) -> vol.Schema:
    fields: dict = {}
    if include_identity:
        fields[vol.Required(CONF_NAME, default=defaults.get(CONF_NAME, "Main Starter"))] = str
        fields[vol.Required(CONF_LOCATION, default=defaults.get(CONF_LOCATION, "bench"))] = (
            selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=list(LOCATIONS), translation_key="location"
                )
            )
        )
        fields[vol.Optional(CONF_LAST_FED)] = selector.DateTimeSelector()
    fields.update(
        {
            vol.Required(
                CONF_BENCH_INTERVAL,
                default=defaults.get(CONF_BENCH_INTERVAL, DEFAULT_BENCH_INTERVAL),
            ): _interval,
            vol.Required(
                CONF_FRIDGE_INTERVAL,
                default=defaults.get(CONF_FRIDGE_INTERVAL, DEFAULT_FRIDGE_INTERVAL),
            ): _interval,
            vol.Required(
                CONF_DUE_SOON,
                default=defaults.get(CONF_DUE_SOON, DEFAULT_DUE_SOON),
            ): vol.All(vol.Coerce(float), vol.Range(min=0, max=168)),
        }
    )
    return vol.Schema(fields)


class SourdoughConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Configure a starter."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        if user_input is None:
            return self.async_show_form(step_id="user", data_schema=_schema({}, True))
        name = user_input.pop(CONF_NAME)
        last_fed = user_input.get(CONF_LAST_FED)
        if hasattr(last_fed, "isoformat"):
            user_input[CONF_LAST_FED] = last_fed.isoformat()
        return self.async_create_entry(
            title=name, data={CONF_STARTER_NAME: name, **user_input}
        )

    @staticmethod
    def async_get_options_flow(config_entry):
        return SourdoughOptionsFlow()


class SourdoughOptionsFlow(config_entries.OptionsFlow):
    """Edit feeding frequencies."""

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(data=user_input)
        defaults = {**self.config_entry.data, **self.config_entry.options}
        return self.async_show_form(
            step_id="init", data_schema=_schema(defaults, False)
        )
