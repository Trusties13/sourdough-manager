"""Constants for Sourdough Manager."""
from homeassistant.const import Platform

DOMAIN = "sourdough_manager"
PLATFORMS = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.CALENDAR,
    Platform.DATE,
    Platform.DATETIME,
    Platform.EVENT,
    Platform.SELECT,
    Platform.SWITCH,
    Platform.TIME,
]

STORAGE_VERSION = 2
SCHEMA_VERSION = 6
STORAGE_KEY_PREFIX = f"{DOMAIN}.starter"

CONF_STARTER_NAME = "starter_name"
CONF_LOCATION = "location"
CONF_BENCH_INTERVAL = "bench_interval_hours"
CONF_FRIDGE_INTERVAL = "fridge_interval_hours"
CONF_DUE_SOON = "due_soon_hours"
CONF_LAST_FED = "last_fed"
CONF_NOTIFICATION_TARGETS = "notification_targets"
CONF_OVERDUE_INTERVAL = "overdue_interval_minutes"
CONF_QUIET_HOURS_ENABLED = "quiet_hours_enabled"
CONF_QUIET_START = "quiet_start"
CONF_QUIET_END = "quiet_end"
CONF_CONFIRM_FEED = "confirm_feed"
CONF_AUDIO_ENABLED = "audio_enabled"
CONF_AUDIO_TTS_ENTITY = "audio_tts_entity"
CONF_AUDIO_TARGETS = "audio_targets"
CONF_AUDIO_LEAD_TIME = "audio_lead_time_hours"
CONF_AUDIO_INTERVAL = "audio_interval_minutes"
CONF_AUDIO_VOLUME = "audio_volume_percent"
CONF_LIGHT_TARGETS = "light_targets"
CONF_LIGHT_COLOR = "light_color"
CONF_LIGHT_FLASH_COUNT = "light_flash_count"
CONF_LIGHT_PULSE_SECONDS = "light_pulse_seconds"
CONF_LIGHT_GAP_SECONDS = "light_gap_seconds"
CONF_PREFERRED_TIME_ENABLED = "preferred_time_enabled"
CONF_PREFERRED_TIME = "preferred_feed_time"
CONF_BENCH_PREFERRED_TIME = "bench_preferred_feed_time"
CONF_FRIDGE_PREFERRED_TIME = "fridge_preferred_feed_time"
CONF_HOLIDAY_MODE_ENTITY = "holiday_mode_entity"

LOCATION_BENCH = "bench"
LOCATION_FRIDGE = "refrigerator"
LOCATIONS = (LOCATION_BENCH, LOCATION_FRIDGE)

DEFAULT_BENCH_INTERVAL = 48.0
DEFAULT_FRIDGE_INTERVAL = 168.0
DEFAULT_DUE_SOON = 12.0
DEFAULT_OVERDUE_INTERVAL = 30.0
DEFAULT_AUDIO_LEAD_TIME = 0.0
DEFAULT_AUDIO_INTERVAL = 60.0
DEFAULT_AUDIO_VOLUME = 60.0
DEFAULT_LIGHT_COLOR = [255, 0, 0]
DEFAULT_LIGHT_FLASH_COUNT = 3
DEFAULT_LIGHT_PULSE_SECONDS = 1.0
DEFAULT_LIGHT_GAP_SECONDS = 0.25
DEFAULT_PREFERRED_TIME = "09:00:00"
DEFAULT_HOLIDAY_MODE_ENTITY = "binary_sensor.holiday_mode"
DEFAULT_QUIET_START = "22:00:00"
DEFAULT_QUIET_END = "07:00:00"
DEFAULT_SNOOZE_HOURS = "1"
SNOOZE_OPTIONS = ("1", "3", "12")
DELAY_OPTIONS = ("1", "3", "tomorrow_morning")
DUPLICATE_FEED_SECONDS = 10
MAX_FEED_HISTORY = 20

EVENT_FEED_RECORDED = f"{DOMAIN}_feed_recorded"
EVENT_DUE_SOON = f"{DOMAIN}_feed_due_soon"
EVENT_OVERDUE = f"{DOMAIN}_feed_overdue"
EVENT_LOCATION_CHANGED = f"{DOMAIN}_location_changed"
EVENT_DEADLINE_DELAYED = f"{DOMAIN}_deadline_delayed"
EVENT_TYPES = (
    "feed_recorded",
    "due_soon",
    "overdue",
    "location_changed",
    "deadline_delayed",
)

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
