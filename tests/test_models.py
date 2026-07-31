"""Tests for focused scheduling calculations."""
import importlib.util
import sys
from datetime import UTC, datetime
from pathlib import Path

models_spec = importlib.util.spec_from_file_location(
    "sourdough_models",
    Path(__file__).parents[1] / "custom_components/sourdough_manager/models.py",
)
models = importlib.util.module_from_spec(models_spec)
assert models_spec.loader is not None
sys.modules[models_spec.name] = models
models_spec.loader.exec_module(models)


def test_next_feed_uses_location_frequency():
    fed = datetime(2026, 7, 25, 9, tzinfo=UTC)
    assert models.next_feed_due(fed, "bench", 48, 168) == datetime(
        2026, 7, 27, 9, tzinfo=UTC
    )
    assert models.next_feed_due(fed, "refrigerator", 48, 168) == datetime(
        2026, 8, 1, 9, tzinfo=UTC
    )


def test_aligns_deadline_to_preferred_local_time():
    due = datetime(2026, 7, 27, 14, 37, tzinfo=UTC)
    assert models.align_deadline_to_preferred_time(
        due, "09:00:00"
    ) == datetime(2026, 7, 27, 9, tzinfo=UTC)


def test_due_and_due_soon_boundaries():
    due = datetime(2026, 7, 27, 9, tzinfo=UTC)
    assert models.schedule_state(
        due, 12, datetime(2026, 7, 26, 20, tzinfo=UTC)
    ) == (False, False)
    assert models.schedule_state(
        due, 12, datetime(2026, 7, 26, 22, tzinfo=UTC)
    ) == (False, True)
    assert models.schedule_state(
        due, 12, datetime(2026, 7, 27, 9, tzinfo=UTC)
    ) == (True, False)


def test_due_today_or_overdue_uses_local_dates():
    due = datetime(2026, 7, 27, 9, tzinfo=UTC)
    assert not models.due_today_or_overdue(
        due, datetime(2026, 7, 26, 23, tzinfo=UTC)
    )
    assert models.due_today_or_overdue(
        due, datetime(2026, 7, 27, 1, tzinfo=UTC)
    )
    assert models.due_today_or_overdue(
        due, datetime(2026, 7, 28, 1, tzinfo=UTC)
    )


def test_overdue_hours():
    due = datetime(2026, 7, 27, 9, tzinfo=UTC)
    assert models.overdue_hours(due, datetime(2026, 7, 27, 17, tzinfo=UTC)) == 8
    assert models.overdue_hours(due, datetime(2026, 7, 27, 8, tzinfo=UTC)) == 0


def test_human_duration():
    assert models.human_duration(0) == "Disabled"
    assert models.human_duration(0.5) == "30 minutes"
    assert models.human_duration(24) == "1 day"
    assert models.human_duration(36) == "1 day 12 hours"
    assert models.human_duration(168) == "7 days"


def test_quiet_hours_across_midnight():
    assert models.quiet_hours_active(
        datetime(2026, 7, 26, 23), True, "22:00:00", "07:00:00"
    )
    assert models.quiet_hours_active(
        datetime(2026, 7, 26, 6), True, "22:00:00", "07:00:00"
    )
    assert not models.quiet_hours_active(
        datetime(2026, 7, 26, 12), True, "22:00:00", "07:00:00"
    )
    assert not models.quiet_hours_active(
        datetime(2026, 7, 26, 23), False, "22:00:00", "07:00:00"
    )


def test_human_clock_range():
    assert models.human_clock_range("22:00:00", "07:30:00") == (
        "10:00 pm to 7:30 am"
    )


def test_overdue_notification_copy_gets_firmer():
    assert models.overdue_notification_copy("Main Starter", 1)[0] == (
        "Main Starter feeding is due"
    )
    assert models.overdue_notification_copy("Main Starter", 3)[0] == (
        "Main Starter feeding is overdue"
    )
    assert models.overdue_notification_copy("Main Starter", 13)[0] == (
        "Main Starter needs feeding"
    )
    assert models.overdue_notification_copy("Main Starter", 25)[0] == (
        "Main Starter is seriously overdue"
    )


def test_audio_reminder_has_independent_lead_time_and_interval():
    due = datetime(2026, 7, 27, 9, tzinfo=UTC)
    assert not models.audio_reminder_due(
        datetime(2026, 7, 27, 6, tzinfo=UTC), due, 2, None, 60
    )
    assert models.audio_reminder_due(
        datetime(2026, 7, 27, 7, tzinfo=UTC), due, 2, None, 60
    )
    assert not models.audio_reminder_due(
        datetime(2026, 7, 27, 8, tzinfo=UTC),
        due,
        2,
        datetime(2026, 7, 27, 7, 30, tzinfo=UTC),
        60,
    )
    assert models.audio_reminder_due(
        datetime(2026, 7, 27, 8, 30, tzinfo=UTC),
        due,
        2,
        datetime(2026, 7, 27, 7, 30, tzinfo=UTC),
        60,
    )


def test_light_restore_data_uses_original_mode_and_brightness():
    assert models.light_restore_data(
        {
            "brightness": 120,
            "color_mode": "hs",
            "hs_color": (30.0, 70.0),
            "rgb_color": (255, 127, 76),
            "effect": "none",
        }
    ) == {
        "brightness": 120,
        "hs_color": (30.0, 70.0),
        "effect": "none",
    }


def test_migrates_existing_active_cycle_and_location():
    migrated = models.migrate_storage(
        {
            "active_cycle": {"fed_at": "2026-07-25T09:00:00+00:00"},
            "location": "refrigerator",
            "feed_history": [{"unused": True}],
        },
        "bench",
    )
    assert migrated == {
        "schema_version": 6,
        "last_fed": "2026-07-25T09:00:00+00:00",
        "location": "refrigerator",
        "location_changed_at": None,
        "last_reminder_for": None,
        "last_overdue_reminder_at": None,
        "last_reminder_sent_at": None,
        "snoozed_until": None,
        "snooze_hours": "1",
        "last_audio_reminder_at": None,
        "last_light_reminder_at": None,
        "reminders_enabled": True,
        "deadline_override": None,
        "delay_option": "1",
        "feed_history": [{"unused": True}],
        "last_event_type": None,
        "last_event_at": None,
        "missed_feed_count": 0,
        "missed_deadline_for": None,
    }


def test_migration_retains_only_twenty_feed_records():
    history = [
        {"fed_at": f"2026-07-{day:02d}T09:00:00+00:00", "location": "bench"}
        for day in range(1, 26)
    ]
    migrated = models.migrate_storage({"feed_history": history}, "bench")
    assert len(migrated["feed_history"]) == 20
    assert migrated["feed_history"][0] == history[5]
