"""Constants for Sourdough Manager."""
from homeassistant.const import Platform

DOMAIN = "sourdough_manager"
PLATFORMS = [Platform.SENSOR, Platform.BUTTON, Platform.NUMBER, Platform.SELECT]
STORAGE_VERSION = 2
STORAGE_KEY_PREFIX = f"{DOMAIN}.starter"

CONF_STARTER_NAME = "starter_name"
CONF_STARTER_HYDRATION = "starter_hydration"
CONF_DEFAULT_FLOUR = "default_flour"
CONF_TEMPERATURE_ENTITY = "temperature_entity"
CONF_DEFAULT_TEMPERATURE = "default_temperature"
CONF_REMINDER_DAYS = "refrigerated_reminder_days"
CONF_VESSEL_TARE = "vessel_tare_g"
CONF_DEFAULT_STARTER = "default_starter_retained_g"
CONF_DEFAULT_WATER = "default_water_added_g"
CONF_DEFAULT_FLOUR_AMOUNT = "default_flour_added_g"
CONF_PROGRAMME = "programme"

DEFAULT_HYDRATION = 100.0
DEFAULT_TEMPERATURE = 22.0
DEFAULT_REMINDER_DAYS = 14
DEFAULT_FLOUR = "bread_flour"
DEFAULT_VESSEL_TARE = 0.0
DEFAULT_STARTER = 30.0
DEFAULT_WATER = 30.0
DEFAULT_FLOUR_AMOUNT = 30.0
DEFAULT_PROGRAMME = "mature"

FLOUR_TYPES = (
    "bread_flour",
    "plain_flour",
    "wholemeal_wheat",
    "rye",
    "spelt",
    "custom_blend",
    "other",
)
PROGRAMMES = ("mature", "new_starter", "refrigerated")

EVENTS = (
    "feed_recorded",
    "peak_marked",
    "refrigerated",
    "removed_from_fridge",
    "cycle_cancelled",
    "discard_recorded",
    "use_recorded",
)
