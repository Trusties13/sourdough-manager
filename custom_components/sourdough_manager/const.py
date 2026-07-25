"""Constants for Sourdough Manager."""
from homeassistant.const import Platform

DOMAIN = "sourdough_manager"
PLATFORMS = [Platform.SENSOR, Platform.BUTTON]
STORAGE_VERSION = 1
STORAGE_KEY_PREFIX = f"{DOMAIN}.starter"

CONF_STARTER_NAME = "starter_name"
CONF_STARTER_HYDRATION = "starter_hydration"
CONF_DEFAULT_FLOUR = "default_flour"
CONF_TEMPERATURE_ENTITY = "temperature_entity"
CONF_DEFAULT_TEMPERATURE = "default_temperature"
CONF_REMINDER_DAYS = "refrigerated_reminder_days"

DEFAULT_HYDRATION = 100.0
DEFAULT_TEMPERATURE = 22.0
DEFAULT_REMINDER_DAYS = 14
DEFAULT_FLOUR = "bread_flour"

EVENTS = (
    "feed_recorded",
    "peak_marked",
    "refrigerated",
    "removed_from_fridge",
    "cycle_cancelled",
    "discard_recorded",
    "use_recorded",
)
