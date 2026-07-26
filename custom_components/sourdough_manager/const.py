"""Constants for Sourdough Manager."""
from homeassistant.const import Platform

DOMAIN = "sourdough_manager"
PLATFORMS = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.DATETIME,
    Platform.SELECT,
]

STORAGE_VERSION = 2
SCHEMA_VERSION = 3
STORAGE_KEY_PREFIX = f"{DOMAIN}.starter"

CONF_STARTER_NAME = "starter_name"
CONF_LOCATION = "location"
CONF_BENCH_INTERVAL = "bench_interval_hours"
CONF_FRIDGE_INTERVAL = "fridge_interval_hours"
CONF_DUE_SOON = "due_soon_hours"
CONF_LAST_FED = "last_fed"
CONF_NOTIFICATION_TARGETS = "notification_targets"

LOCATION_BENCH = "bench"
LOCATION_FRIDGE = "refrigerator"
LOCATIONS = (LOCATION_BENCH, LOCATION_FRIDGE)

DEFAULT_BENCH_INTERVAL = 48.0
DEFAULT_FRIDGE_INTERVAL = 168.0
DEFAULT_DUE_SOON = 12.0

EVENT_FEED_RECORDED = f"{DOMAIN}_feed_recorded"
EVENT_DUE_SOON = f"{DOMAIN}_feed_due_soon"
EVENT_OVERDUE = f"{DOMAIN}_feed_overdue"
EVENT_LOCATION_CHANGED = f"{DOMAIN}_location_changed"

OBSOLETE_ENTITY_KEYS = (
    "status",
    "expected_peak",
    "peak_window_start",
    "peak_window_end",
    "current_weight",
    "feed_ratio",
    "hydration",
    "cycle_progress",
    "prediction_confidence",
    "average_temperature",
    "last_peak_duration",
    "total_weight_with_vessel",
    "suggested_discard",
    "suggested_water",
    "suggested_flour",
    "feeding_count",
    "programme_day",
    "programme_phase",
    "instructions",
    "mark_peak",
    "record_feed",
    "refrigerate",
    "remove_from_fridge",
    "cancel_cycle",
    "starter_retained_g",
    "water_added_g",
    "flour_added_g",
    "flour_type",
)
